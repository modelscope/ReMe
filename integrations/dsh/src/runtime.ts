import type { LoggerLike, ReMeClientLike, ReMeMessage } from "./reme/types.js";
import { messagesDay, nextDailyRun } from "./scheduling.js";
import { captureMessage, remeSessionId } from "./messages.js";
import { MemoryOutbox } from "./outbox.js";
import { safeError } from "./endpoint.js";
import type { DshSession, ReMeConfig, SessionEvent } from "./types.js";
import type { ReMeRuntimeSnapshot, ReMeRuntimeTask } from "./runtime-status.js";

export class ReMeRuntime {
  private readonly states = new Map<string, ReMeMessage[]>();
  private readonly configSource: () => ReMeConfig;
  private readonly outbox: MemoryOutbox;
  private memoryTask: Promise<void> | null = null;
  private memoryWake = false;
  private activeMemoryTask: ReMeRuntimeTask | null = null;
  private memoryController: AbortController | null = null;
  private readonly retryTimers = new Map<
    string,
    ReturnType<typeof setTimeout>
  >();
  private readonly failures = new Map<string, number>();
  private memoryError: string | undefined;
  private captureError: string | undefined;
  private dreamTimer: ReturnType<typeof setTimeout> | null = null;
  private dreamScheduleGeneration = 0;
  private dreamTask: Promise<void> | null = null;
  private dreamController: AbortController | null = null;
  private started = false;
  private stopping = false;
  private closed = false;
  private taskSequence = 0;
  private readonly recentTasks: ReMeRuntimeTask[] = [];
  private nextDreamAt: string | undefined;
  private dreamLastStartedAt: string | undefined;
  private dreamLastFinishedAt: string | undefined;
  private dreamLastResult: "completed" | "failed" | "cancelled" | undefined;
  private dreamLastError: string | undefined;

  constructor(
    readonly client: ReMeClientLike,
    config: ReMeConfig | (() => ReMeConfig),
    readonly logger: LoggerLike = console,
  ) {
    this.configSource = typeof config === "function" ? config : () => config;
    this.outbox = new MemoryOutbox(this.configSource().autoMemoryQueueDir);
  }

  capture(session: DshSession, event: SessionEvent): void {
    const config = this.configSource();
    if (this.stopping || !config.autoMemoryEnabled) return;
    if (event.type === "turn/start") {
      this.states.set(session.id, []);
      return;
    }
    const messages = this.states.get(session.id);
    if (!messages) return;
    const message = captureMessage(event, session.id);
    if (message) messages.push(message);
    if (event.type !== "turn/end") return;
    const data = isRecord(event.data) ? event.data : undefined;
    const reason = isRecord(data?.reason) ? data.reason.kind : undefined;
    if (
      (reason === "completed" || reason === "max-tokens") &&
      messages.some((item) => item.role === "user") &&
      messages.some((item) => item.role === "assistant")
    ) {
      try {
        this.outbox.append(
          config.endpoint,
          remeSessionId(session.id),
          messagesDay(messages, config.timezone),
          messages,
          config.autoMemoryInterval,
        );
      } catch (error) {
        this.captureError = safeError(error);
        this.recordMemoryError(error);
      }
    }
    this.states.set(session.id, []);
    void this.drain();
  }

  /** Drain ready batches serially; failed batches stay on disk for the retry timer. */
  drain(): Promise<void> {
    if (this.closed) return Promise.resolve();
    if (this.memoryTask) {
      this.memoryWake = true;
      return this.memoryTask;
    }
    if (this.retryTimers.has("*") || !this.configSource().autoMemoryEnabled)
      return Promise.resolve();
    this.memoryController = new AbortController();
    const controller = this.memoryController;
    this.memoryTask = Promise.resolve()
      .then(async () => {
        while (
          !controller.signal.aborted &&
          this.configSource().autoMemoryEnabled
        ) {
          const next = this.outbox.next(this.retryTimers);
          if (!next) return;
          const { name, batch } = next;
          const messages = batch.turns.flat();
          const task: ReMeRuntimeTask = {
            id: `${batch.id}-${++this.taskSequence}`,
            phase: "running",
            queuedAt: new Date(batch.createdAt).toISOString(),
            startedAt: new Date().toISOString(),
            turns: batch.turns.length,
            messages: messages.length,
          };
          this.activeMemoryTask = task;
          this.recentTasks.unshift(task);
          this.recentTasks.length = Math.min(this.recentTasks.length, 20);
          try {
            const result = await this.client.autoMemory(
              messages,
              batch.sessionId,
              {
                date: batch.date,
                endpoint: batch.endpoint,
                requestId: batch.id,
                signal: controller.signal,
              },
            );
            if (controller.signal.aborted) {
              task.phase = "cancelled";
              return;
            }
            if (!result.ok)
              throw new Error(
                `ReMe automatic-memory request failed (HTTP ${
                  result.status ?? 0
                })`,
              );
            this.outbox.acknowledge(name);
            task.phase = "completed";
            // Reply text and file names can contain personal information.
            this.failures.delete(batch.endpoint);
            if (!this.retryTimers.size) this.memoryError = undefined;
          } catch (error) {
            task.phase = controller.signal.aborted ? "cancelled" : "failed";
            task.error = safeError(error);
            this.recordMemoryError(error);
            if (this.stopping) return;
            this.scheduleRetry(batch.endpoint);
          } finally {
            task.finishedAt = new Date().toISOString();
            this.activeMemoryTask = null;
          }
        }
      })
      .catch((error: unknown) => {
        this.recordMemoryError(error);
        this.scheduleRetry();
      })
      .finally(() => {
        this.memoryTask = null;
        this.memoryController = null;
        if (this.memoryWake && !this.stopping) {
          this.memoryWake = false;
          return this.drain();
        }
      });
    return this.memoryTask;
  }

  private recordMemoryError(error: unknown): void {
    this.memoryError = safeError(error);
    this.log("warn", "auto_memory_failed", { error: this.memoryError });
  }

  private scheduleRetry(endpoint = "*"): void {
    if (
      this.stopping ||
      this.retryTimers.has(endpoint) ||
      !this.configSource().autoMemoryEnabled
    )
      return;
    const config = this.configSource();
    const failures = this.failures.get(endpoint) ?? 0;
    this.failures.set(endpoint, failures + 1);
    const delay = Math.min(
      config.autoMemoryRetryMaxMs,
      config.autoMemoryRetryMs * 2 ** Math.min(failures, 20),
    );
    const timer = setTimeout(() => {
      this.retryTimers.delete(endpoint);
      void this.drain();
    }, delay);
    timer.unref?.();
    this.retryTimers.set(endpoint, timer);
  }

  private clearRetries(): void {
    for (const timer of this.retryTimers.values()) clearTimeout(timer);
    this.retryTimers.clear();
    this.failures.clear();
  }

  start(): void {
    if (this.started || this.stopping) return;
    this.started = true;
    // A previous Host may have stopped before the batching interval was reached.
    try {
      this.outbox.flush();
    } catch (error) {
      this.outbox.close();
      throw error;
    }
    void this.drain();
    if (this.configSource().autoDreamEnabled)
      this.scheduleDream(this.dreamScheduleGeneration);
  }

  /** Apply settings without discarding captured work or replacing the runtime. */
  reconfigure(): void {
    if (this.stopping) return;
    this.clearRetries();
    if (!this.configSource().autoMemoryEnabled) this.states.clear();
    if (this.configSource().autoMemoryEnabled) {
      this.outbox.flush();
      void this.drain();
    }
    if (!this.started) return;
    this.dreamScheduleGeneration += 1;
    if (this.dreamTimer) clearTimeout(this.dreamTimer);
    this.dreamTimer = null;
    this.nextDreamAt = undefined;
    if (this.configSource().autoDreamEnabled)
      this.scheduleDream(this.dreamScheduleGeneration);
  }

  private scheduleDream(generation: number): void {
    const config = this.configSource();
    if (
      generation !== this.dreamScheduleGeneration ||
      this.stopping ||
      !config.autoDreamEnabled
    )
      return;
    let delay: number;
    try {
      delay =
        config.dreamIntervalMs > 0
          ? config.dreamIntervalMs
          : nextDailyRun(config.dreamCron, config.timezone).getTime() -
            Date.now();
    } catch (error) {
      this.log("warn", "auto_dream_schedule_invalid", {
        error: safeError(error),
      });
      return;
    }
    this.nextDreamAt = new Date(Date.now() + delay).toISOString();
    this.dreamTimer = setTimeout(() => {
      this.dreamTimer = null;
      this.nextDreamAt = undefined;
      void this.runDream().finally(() => this.scheduleDream(generation));
    }, delay);
    this.dreamTimer.unref?.();
  }

  async runDream(): Promise<void> {
    if (this.stopping) return;
    if (this.dreamTask) return this.dreamTask;
    const config = this.configSource();
    this.dreamController = new AbortController();
    this.dreamLastStartedAt = new Date().toISOString();
    this.dreamLastFinishedAt = undefined;
    this.dreamLastResult = undefined;
    this.dreamLastError = undefined;
    this.dreamTask = (async () => {
      try {
        const result = await this.client.autoDream({
          hint: config.dreamHint,
          signal: this.dreamController?.signal,
        });
        this.log(
          result.ok ? "debug" : "warn",
          result.ok ? "auto_dream_complete" : "auto_dream_failed",
          {
            error: result.ok ? undefined : safeError(result.error),
          },
        );
        this.dreamLastResult = result.ok ? "completed" : "failed";
        this.dreamLastError = result.ok
          ? undefined
          : safeError(result.error || "ReMe rejected the Auto Dream request");
      } catch (error) {
        this.dreamLastResult = this.dreamController?.signal.aborted
          ? "cancelled"
          : "failed";
        this.dreamLastError = safeError(error);
        this.log("warn", "auto_dream_failed", {
          error: safeError(error),
        });
      }
    })().finally(() => {
      this.dreamLastFinishedAt = new Date().toISOString();
      this.dreamTask = null;
      this.dreamController = null;
    });
    return this.dreamTask;
  }

  async dispose(session: DshSession): Promise<void> {
    this.states.delete(session.id);
    this.outbox.flush(remeSessionId(session.id));
    void this.drain();
  }

  async disposeAll(): Promise<void> {
    if (this.stopping) return;
    this.stopping = true;
    this.started = false;
    this.states.clear();
    this.dreamScheduleGeneration += 1;
    if (this.dreamTimer) clearTimeout(this.dreamTimer);
    this.clearRetries();
    this.dreamTimer = null;
    this.nextDreamAt = undefined;
    this.dreamController?.abort();
    try {
      this.outbox.flush();
      await this.withinShutdownBudget(
        Promise.all([this.drain(), this.dreamTask]).then(() => undefined),
        () => {
          this.memoryController?.abort();
          this.dreamController?.abort();
        },
      );
    } finally {
      this.memoryController?.abort();
      this.outbox.close();
      this.closed = true;
    }
  }

  /** Return queue counts and bounded diagnostics without reply content. */
  snapshot(): ReMeRuntimeSnapshot {
    const config = this.configSource();
    const queued = this.outbox.stats();
    const running = this.activeMemoryTask === null ? 0 : 1;
    return {
      phase: this.closed
        ? "stopped"
        : this.stopping
        ? "stopping"
        : this.started
        ? "running"
        : "stopped",
      autoMemory: {
        enabled: config.autoMemoryEnabled,
        interval: config.autoMemoryInterval,
        activeSessions: this.states.size,
        queuedTurns: queued.turns,
        tasksRunning: running,
        tasksQueued: Math.max(0, queued.batches - running),
        recentTasks: this.recentTasks.map((task) => ({ ...task })),
        ...(this.captureError || this.memoryError
          ? { lastError: this.captureError || this.memoryError }
          : {}),
      },
      autoDream: {
        enabled: config.autoDreamEnabled,
        cron: config.dreamCron,
        timezone: config.timezone,
        running: this.dreamTask !== null,
        ...(this.nextDreamAt ? { nextRunAt: this.nextDreamAt } : {}),
        ...(this.dreamLastStartedAt
          ? { lastStartedAt: this.dreamLastStartedAt }
          : {}),
        ...(this.dreamLastFinishedAt
          ? { lastFinishedAt: this.dreamLastFinishedAt }
          : {}),
        ...(this.dreamLastResult ? { lastResult: this.dreamLastResult } : {}),
        ...(this.dreamLastError ? { lastError: this.dreamLastError } : {}),
      },
    };
  }

  private async withinShutdownBudget(
    task: Promise<void>,
    abort: () => void,
  ): Promise<void> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      await Promise.race([
        task,
        new Promise<void>((resolve) => {
          timer = setTimeout(() => {
            abort();
            resolve();
          }, this.configSource().shutdownTimeoutMs);
        }),
      ]);
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  private log(
    level: "debug" | "warn",
    event: string,
    data: Record<string, unknown>,
  ): void {
    const method = this.logger[level] ?? this.logger.log;
    method?.call(this.logger, `[reme-memory] ${event}`, data);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
