# Payment trajectory compaction pilot

Compare full history, ReMe decision-model previews and ordinary Qwen summaries on the synthetic payment incident
collected with Hermes. This is a fixed pilot exam, not a general-purpose benchmark. The source must contain the
`PAY-4827` / `INV-731` / `CH-991` incident. Provider calls are opt-in and outputs must be outside the repository.

From the repository root, with the development environment and `reme-ai[decision]` installed:

```bash
python benchmark/compaction/run.py --live \
  --trajectory /path/to/trajectory.full.json \
  --output /path/outside/repository/experiment
```

Credentials come from the repository `.env`: `LLM_API_KEY`, `LLM_BASE_URL`, `DECISION_MODEL_API_KEY`, and optional
`DECISION_MODEL_NAME` / `DECISION_MODEL_BASE_URL`. Answering and summarization default to `qwen3.8-max`.

The final assistant report is excluded to prevent answer leakage. The original system prompt and initial user request
remain unchanged in all arms. Jev defaults and a short-history diagnostic (`preserve_recent_messages=0`,
`preview_chars=80`) are separate arms; the latter is not a proposed production default. Ordinary summarization reads
all tool history, then replaces it with one structured summary. This is a direct Qwen summary baseline, not the Hermes
automatic threshold/compaction pipeline. No arm can retrieve the archive during evaluation.

The exam contains ten exact fact checks and three structured repair-plan checks, frozen before inference. Each context
is evaluated three times at temperature zero, without an LLM judge. Identical contexts reuse the same evaluations.
Reported prompt tokens come from Qwen usage and include the common instructions and exam. They are not billing savings.
Compression is generated once per arm; repeated answering does not measure compression variability or independent tasks.

To examine summary-length sensitivity, use a fresh output directory:

```bash
python benchmark/compaction/run.py --live \
  --trajectory /path/to/trajectory.full.json \
  --output /path/outside/repository/summary500 \
  --summary-words 500 --summary-max-tokens 2048
```

Artifacts include the frozen protocol and exam, source, proposed contexts, decisions, Qwen request/response bodies,
checks, usage and a report. HTTP headers and credentials are not saved. The original trajectory is checked for changes.
A truncated summary is rejected rather than silently counted as a valid compression baseline.

This small synthetic sample cannot establish task success, reliability on real long histories, or superiority at a
matched token budget. Repair-plan checks do not execute a patch. Investigate omitted facts, recovery, prompt-cache costs
and longer multi-stage tasks before choosing a production strategy.

## Matched-budget span experiment

See [评测方案与实测结果（中文）](./RESULTS.md) for the frozen protocol, full comparison table, omissions and limits.

`span_experiment.py` tests a separate experimental policy: split long tool observations on line boundaries,
score complete spans with Jev, then select original spans by descending usefulness within a fixed budget. It does
not change the production step's conservative probability threshold. Short code and JSON observations stay whole.
Every selected span retains its file and character offsets; the archived source remains unchanged.

```bash
python -m benchmark.compaction.span_experiment --live \
  --trajectory /path/to/trajectory.full.json \
  --output /path/outside/repository/span-experiment \
  --tokenizer /path/to/cached/qwen/tokenizer.json
```

The runner needs the optional `tokenizers` Python package and a local tokenizer JSON. No new production dependency
is required. The local tokenizer is a budgeting proxy, not a claim about the provider's exact tokenizer. Its hash is
recorded and actual API prompt usage is reported separately.

The frozen defaults compare 600 and 1000 evidence-token allowances against full evidence, deterministic head/tail
clipping and ordinary structured Qwen summaries. All arms preserve the same original system/user instructions and
use a normalized evidence bundle, rather than the original API tool-message framing. Budgets are identical upper
bounds, not forced exact lengths. Oversized summaries are marked invalid; truncated responses abort the run.
No arm can recover omitted content during evaluation. There is no threshold tuning against exam answers.

Both the original short payment trajectory and a controlled long-log variant are evaluated. The latter inserts
180 routine health-check lines around the original log events, preserving the original text. This is one task with
a noise augmentation, not two independent tasks or a newly collected trajectory. Source variants, exam, gold answers
and settings are saved before inference. Jev scoring receives the task and evidence, never the exam or gold answers.

Alongside ten exact fact checks, generated retry functions run against six deterministic behavioral cases:
success, timeout followed by success with one idempotency key, no retry on HTTP 402/422, exhaustion raising the last
timeout, and distinct keys for separate payments. `repair_check.py` accepts only a restricted function grammar and
bounded iteration with inert clients; it provides no file, network or payment access. This is a small function-level
repair test, not a full agent task benchmark. Each context is answered twice; each summary is generated once.

Reports include evidence and actual input tokens, factual accuracy, repair pass rates, compaction latency, usage,
full requests/responses and source offsets. Compression savings alone do not establish lower total cost or better
quality. The experiment may fail to show a Jev advantage; report that outcome without changing the frozen budgets.
