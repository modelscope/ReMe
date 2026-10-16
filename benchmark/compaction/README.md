# Context compaction: fixed summary + selected evidence

A **14-query fixture panel** with predefined answers and rule scoring: four primary tasks and ten short/query-only
controls. See [queries, answers and frozen settings](./STUDY.md) and [measured results](./RESULTS.md).

Hermes collects the source through real `read_file` calls. ReMe's experiment then compares Full context, a frozen Qwen
summary S and forced **Hermes small-window summary H**, each with Jev Top 0–5. Scored answering calls Qwen directly;
there is no resumed Hermes tool loop or archive recovery. Production `compact_context` is separate.

## Run

Use ReMe's development environment plus optional `tokenizers`. Collection and native generation need a separately
installed Hermes environment, also able to import `tokenizers`. Credentials come from ReMe's `.env`:
`LLM_API_KEY`, `LLM_BASE_URL`, `DECISION_MODEL_API_KEY`, and optional `DECISION_MODEL_NAME` / `DECISION_MODEL_BASE_URL`.
All commands require `--live`; outputs must be new directories outside this repository.

```bash
# Freeze all task/answer definitions, then collect 13 new read-only trajectories.
# Reuse the pinned original payment trajectory as the fourteenth source.
python -m benchmark.compaction.suite_collect --live \
  --hermes /path/to/hermes-agent \
  --hermes-python /path/to/hermes-environment/bin/python \
  --payment-trajectory /path/to/original/trajectory.full.json \
  --output /path/outside/repository/corpus

# Freeze S and Jev rankings, then run the seven-method Top-N sweep.
python -m benchmark.compaction.suite_run --live \
  --corpus /path/outside/repository/corpus/corpus.json \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/evaluation

# Generate the native-adapter summaries and add the eighth method.
# An existing complete --native directory reuses all frozen native generations.
python -m benchmark.compaction.suite_native --live \
  --corpus /path/outside/repository/corpus/corpus.json \
  --evaluation /path/outside/repository/evaluation \
  --native /path/outside/repository/native-generations \
  --hermes /path/to/hermes-agent \
  --hermes-python /path/to/hermes-environment/bin/python \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/combined-results

# Reuse all frozen summaries/rankings and 672 answers; add only H + Top 1–5.
python -m benchmark.compaction.suite_fusion --live \
  --corpus /path/outside/repository/corpus/corpus.json \
  --evaluation /path/outside/repository/evaluation \
  --combined /path/outside/repository/combined-results \
  --native /path/outside/repository/native-generations \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/dual-summary-results
```

The task definitions use local Hermes commit `30463589eb54fa0f48724594cc0e98e6b995729b` (MIT). The recorded study uses
`qwen3.8-max`, three summary/ranking generations and two answers per context: **546 contexts, 1,092 answers across thirteen methods**.
Provider requests are bounded to four at a time. Raw files, sessions, wire bodies, code snapshots and per-field grades stay
outside git; existing runs are never overwritten.

S and H each remain byte-identical across their five fusion variants; both use the same Jev selections.
Top N means a strict descending-score prefix, without a probability threshold, skipping or truncation; selected units are rendered in source order. When a task has fewer
than N units, all available units are retained and `actual_n` records the count. The original payment source has ten
units (maximum Top 10); this study sweeps Top 1–5 with task-specific unit counts.

The native baseline invokes Hermes' actual summary generator with an explicit small-window adapter: legacy template,
S-matched body budget, final word constraint, native provenance validation, and body-only downstream framing. It bypasses
normal triggers/head-tail selection and **must actually shorten input**; it is not the unchanged automatic Hermes policy.
See [the exact simulation settings and preflight disclosures](./STUDY.md#added-baseline-hermes-small-window-summary-adapter).

For the recorded format amendment, native summaries used the pre-amendment source files: pass
`--native-evaluation /path/to/pre-amendment/evaluation` when extending that run. The extension verifies its source hash
and permits only the held-out `exam` field to differ; the summary generator never receives that field.

`costs.json` reports standalone summary/ranking input and output overhead separately from answer usage, including
recorded retries. Token counts do not apply model prices or cache discounts and are not monetary savings.
