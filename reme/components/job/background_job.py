"""Long-running background job with optional supervisor."""

import asyncio
import contextlib
import random
import threading
import time
from concurrent.futures import Future

from .base_job import BaseJob
from ..component_registry import R
from ..runtime_context import RuntimeContext
from ...schema import Response


@R.register("background")
class BackgroundJob(BaseJob):
    """Long-running job started by Application._start; runs __call__ until close.

    Subclasses override __call__ (or use the default step-based body). If
    supervisor=True (default) and __call__ raises, it is restarted with
    exponential backoff (backoff_base * 2**attempt, capped at backoff_cap)
    plus ±50% jitter. __call__ must NOT swallow exceptions, otherwise the
    supervisor cannot trigger a restart.

    On close, the stop_event is set and the task is given up to
    ``close_timeout`` seconds to exit gracefully; after that cancellation is
    requested on its event loop and close waits for the actual worker to exit.
    Cancellation of close is propagated only after worker cleanup finishes.
    Job bodies must cooperate with cancellation, including in thread-pool mode.
    If a single run survives at least ``attempt_reset_after`` seconds before
    crashing, the backoff attempt counter resets — so a long-stable job that
    eventually crashes restarts quickly rather than at the capped delay.
    """

    def __init__(
        self,
        supervisor: bool = True,
        backoff_base: float = 1.0,
        backoff_cap: float = 60.0,
        close_timeout: float = 5.0,
        attempt_reset_after: float = 60.0,
        use_thread_pool: bool = False,
        **kwargs,
    ):
        # Background jobs are long-running loops, not request-shaped callables —
        # forced off so they never get registered as service tools.
        kwargs.pop("enable_serve", None)
        super().__init__(enable_serve=False, **kwargs)
        self.supervisor: bool = supervisor
        self.backoff_base: float = backoff_base
        self.backoff_cap: float = backoff_cap
        self.close_timeout: float = close_timeout
        self.attempt_reset_after: float = attempt_reset_after
        self.use_thread_pool: bool = use_thread_pool
        self._stop_event: asyncio.Event | threading.Event | None = None
        self._task: asyncio.Future | None = None
        self._executor_future: Future | None = None
        self._worker_lock = threading.Lock()
        self._worker_task: asyncio.Task | None = None

    async def _start(self) -> None:
        await super()._start()
        if self.use_thread_pool and self.app_context.thread_pool:
            self._stop_event = threading.Event()
            self._executor_future = self.app_context.thread_pool.submit(self._run_in_thread)
            self._task = asyncio.wrap_future(self._executor_future)
        else:
            self._stop_event = asyncio.Event()
            self._task = asyncio.create_task(self._run_with_supervisor())

    def _run_in_thread(self) -> None:
        """Keep executor completion tied to actual event-loop shutdown."""
        with contextlib.suppress(asyncio.CancelledError):
            asyncio.run(self._run_thread_task())

    async def _run_thread_task(self) -> None:
        with self._worker_lock:
            self._worker_task = asyncio.current_task()
        try:
            # close() may have set stop before the worker published its task.
            if not self._stop_event.is_set():
                await self._run_with_supervisor()
        finally:
            # Keep cancellation from targeting a loop that has already closed.
            with self._worker_lock:
                self._worker_task = None

    def _cancel_task(self) -> None:
        if self._executor_future is None:
            self._task.cancel()
            return
        # Cancel queued work without waiting for another long-running job to free
        # a worker. If already running, cancel the coroutine on its own loop.
        self._executor_future.cancel()
        with self._worker_lock:
            if self._worker_task is not None:
                self._worker_task.get_loop().call_soon_threadsafe(self._worker_task.cancel)

    async def _close(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        try:
            await self._shutdown_task()
        finally:
            await super()._close()

    async def _shutdown_task(self) -> None:
        """Wait for graceful exit, then request cancellation and await completion."""
        if self._task is None:
            return

        async def wait_for_exit() -> None:
            try:
                try:
                    # A timeout must not cancel the executor's completion future.
                    await asyncio.wait_for(asyncio.shield(self._task), timeout=self.close_timeout)
                except asyncio.TimeoutError:
                    self._cancel_task()
                    await self._task
            except asyncio.CancelledError:
                pass  # The worker or queued executor future was cancelled.
            except Exception:
                self.logger.exception(f"Background task '{self.name}' raised during close")

        # Shield the whole shutdown so repeated caller cancellations cannot
        # interrupt worker cleanup or cancel the executor's completion future.
        shutdown = asyncio.create_task(wait_for_exit())
        cancelled = None
        while not shutdown.done():
            try:
                await asyncio.shield(shutdown)
            except asyncio.CancelledError as exc:
                cancelled = exc
        shutdown.result()
        self._task = None
        self._executor_future = None
        if cancelled is not None:
            raise cancelled

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with ±50% jitter, capped at backoff_cap."""
        capped = min(self.backoff_base * (2**attempt), self.backoff_cap)
        return min(capped * (0.5 + random.random()), self.backoff_cap)

    async def _wait_or_stop(self, delay: float) -> None:
        """Sleep up to delay, returning immediately when stop_event is set."""
        assert self._stop_event is not None
        if isinstance(self._stop_event, threading.Event):
            self._stop_event.wait(timeout=delay)
        else:
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    async def _run_with_supervisor(self) -> None:
        assert self._stop_event is not None
        attempt = 0
        while not self._stop_event.is_set():
            started_at = time.monotonic()
            try:
                await self()
                return
            except Exception as e:
                if not self.supervisor:
                    raise
                # A long-stable run that just crashed restarts fresh rather than at the capped delay.
                if time.monotonic() - started_at >= self.attempt_reset_after:
                    attempt = 0
                delay = self._backoff_delay(attempt)
                self.logger.exception(f"job body crashed, restart in {delay:.2f}s error={e}")
                attempt += 1
                await self._wait_or_stop(delay)

    async def __call__(self, **kwargs) -> Response:
        """Default body: run steps in order; errors propagate to supervisor."""
        self.check_enabled()
        self._record_call()
        merged = {**self.kwargs, **kwargs}
        context = RuntimeContext(stop_event=self._stop_event, **merged)
        for step in self._build_steps():
            await step(context)
        return context.response
