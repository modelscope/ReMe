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


To render the English comparison chart from the saved 2026-10-15 results, install optional `matplotlib` in your
plotting environment and run from the repository root (no provider calls):

```bash
python -m benchmark.compaction.plot_results \
  --results /path/outside/repository/span-experiment/results.json \
  --output docs/figure/decision-compaction-benchmark.svg
```

The chart shows the controlled long-log variant at the 1000-token evidence allowance, including all four arms.
Axes start at zero; timings that were not measured are labeled explicitly. All plotted values come from `results.json`.

## Hybrid summary and exact-evidence experiment

`hybrid_experiment.py` compares summary-only, Jev-selected evidence, head/tail clipping, three hybrid allocations
(70/30, 50/50, 30/70 summary/evidence), and a 50/50 recency-selected hybrid control. Budgets are 600, 1000 and
1600 tokens, including headings and source citations. Each case/arm/budget has two independent compression requests
and two answers per context. Jev scores are reused across budgets/allocations within each compression repetition.

```bash
python -m benchmark.compaction.hybrid_experiment --live \
  --trajectory /path/to/trajectory.full.json \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/hybrid-experiment
```

Credentials and optional tokenizer requirements match the span experiment. The primary matrix has 132 contexts,
up to 264 evaluation answers and 90 summaries. Real provider calls incur charges. Outputs cannot overwrite an existing
run or be written inside the repository. The protocol, source cases, exam, gold data and experiment code are saved
before model calls. Over-budget/truncated generations remain invalid; they are not tuned against exam answers.

This is **direct Qwen inference**, not continuation inside the Hermes agent loop. Payment input comes from the earlier
Hermes-collected synthetic trajectory; its long-log version is a controlled augmentation. The independent replica
case is a deterministic synthetic fixture. Payment repair functions run six executable tests. Replica outputs receive
five structured procedure checks; no live operation or end-to-end agent execution occurs.

All arms share a new event splitter: short files stay whole; long log lines with a shared invoice, trace or request ID
are grouped, and other lines form bounded blocks. Each original character range remains recoverable. Compare the
arms within this experiment; changes from the previous pilot cannot be attributed solely to combining strategies.
Hybrid summaries receive all source evidence plus the selected original snippets, with instructions to avoid repeating
those snippets. Unused allocation is not transferred between summary and evidence after generation.

Artifacts include `protocol.json`, per-case `*.source.json`, exact contexts, Jev/Qwen request/response bodies,
`results.json`, `aggregate.json`, `REPORT.md` and `validation.json`. Aggregation reports valid/attempted compressions,
mean exact fact accuracy, all-facts-correct rate, task-check pass rate, actual prompt tokens and compaction latency.
Scores are descriptive: two task families and repeated generations do not establish broad statistical superiority.


### Freeze the summary, then append evidence

The [hybrid and incremental results](./HYBRID_RESULTS.md) distinguish fixed-budget reallocation from genuinely
incremental evidence. The latter keeps every baseline summary byte unchanged and appends at most 200/400 evidence
tokens. A recency-selected 400-token control isolates the contribution of decision ranking. Total input increases.
The supplemental protocol was frozen before its additional calls; it is a post-hoc diagnostic, not the initial matrix.

```bash
python -m benchmark.compaction.frozen_summary_experiment --live \
  --primary /path/outside/repository/hybrid-experiment \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/incremental-experiment

python -m benchmark.compaction.analyze_hybrid \
  --primary /path/outside/repository/hybrid-experiment \
  --incremental /path/outside/repository/incremental-experiment \
  --output /path/outside/repository/incremental-experiment/analysis.json

python -m benchmark.compaction.plot_results --incremental \
  --results /path/outside/repository/incremental-experiment/analysis.json \
  --output docs/figure/decision-compaction-incremental.svg
```

The append experiment reuses 600/1000-token baseline summaries and their answers, generates six additional 300-token
baselines, then freezes their text hashes. It requires the primary run with its default two compression generations
and two answers. Invalid new baselines remain invalid; their append groups are not generated. No new Jev calls are
needed because primary scores are reused. Remaining provider calls are opt-in and outputs stay outside the repository.
The analyzer replays strict grading and reports narrowly normalized number/boolean/line formats as a separate,
post-hoc content diagnostic. It never overwrites original scores or changes evidence selection.
Use `plot_results --hybrid` with the primary `aggregate.json` to render the fixed-budget heatmap.


### Summary-aware incremental selection

`summary_aware_experiment.py` is a separately registered post-hoc control. It supplies the frozen summary to Jev and
scores missing or insufficiently precise information. Both this arm and its task-only control retain only scores at
least 0.5 and append at most 400 evidence tokens. Identical contexts reuse answers. No summary text is regenerated.

```bash
python -m benchmark.compaction.summary_aware_experiment --live \
  --incremental /path/outside/repository/incremental-experiment \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/summary-aware-experiment

python -m benchmark.compaction.analyze_hybrid \
  --primary /path/outside/repository/hybrid-experiment \
  --incremental /path/outside/repository/incremental-experiment \
  --aware /path/outside/repository/summary-aware-experiment \
  --output /path/outside/repository/incremental-experiment/analysis.json

python -m benchmark.compaction.plot_results --aware \
  --results /path/outside/repository/incremental-experiment/analysis.json \
  --output docs/figure/decision-compaction-summary-aware.svg
```

This makes new decision calls and may make new Qwen answering calls. It uses the valid frozen baselines from the
incremental experiment, including their exact stored hashes. Report every arm, additional input cost and failed
baseline; do not treat post-hoc gains on these same tasks as held-out validation or guaranteed monotonic improvement.
