# Experiment settings and reproducibility

This describes the **13-method comparison** reported in [RESULTS.md](./RESULTS.md): Full context, generic summary S
and Hermes compaction summary H, each with Jev Top 0–5. Top 0 means summary only.
[STUDY.md](./STUDY.md) defines the queries, fixed answers, scoring rules and protocol amendments.

## Models and agent framework

| Role | Recorded configuration |
| --- | --- |
| Trajectory collection | Hermes Agent `AIAgent`, commit `30463589eb54fa0f48724594cc0e98e6b995729b` |
| Collection model | `qwen3.8-max`, custom OpenAI-compatible Chat Completions endpoint |
| Generic summary S | Direct `qwen3.8-max` call; handoff prompt in [`cases.py`](./cases.py) |
| Hermes summary H | Same `qwen3.8-max`; Hermes `ContextCompressor._generate_summary`, `tail_mode=legacy` |
| Decision/ranking | Jev; recorded resolved response model **`jev-1.13.0`**, through AgentScope/TypeSafe |
| Answering | Direct `qwen3.8-max`, no resumed agent/tool loop |
| Grading | Deterministic, recursive type-strict JSON field checks; no LLM judge |
| Experiment implementation | ReMe commit `50c2c806446c7ae6acc66217afd6e5edc2114046` |

H is **Hermes compaction summary under a small-budget setting**. It reuses Hermes' serialization, structured checkpoint
prompt, redaction and provenance validation. The experiment overrides the summary budget and appends a total word limit,
then removes the native control prefix using Hermes' helper. It invokes summary generation directly rather than
`compress()`: automatic triggering, head/tail-window selection and post-compression conversation repair are outside
this comparison. This is more specific than calling H a modified version of all Hermes context management.

The Qwen alias is what the requests and captured answering responses identify; an immutable provider weight revision
was not supplied. Service-side updates and nondeterminism can change new-run results even at temperature zero.
Use the same `LLM_BASE_URL` service for the closest rerun; this endpoint and API keys are supplied privately in `.env`.
The endpoint was verified as the public China (Beijing) DashScope endpoint; API keys remain private.
The chart uses the published USD list-price schedule below rather than an account invoice.

## Runtime dependencies

Two separate Python environments were used. These versions were **verified from the retained environments after the
run**, not from a pre-run lockfile; they are a reproduction reference rather than proof of a fully locked installation.
The local run used Python **3.13.3**, macOS arm64. No local GPU performs inference.

| Package | ReMe evaluation environment | Hermes collection/summary environment |
| --- | --- | --- |
| `openai` | 2.53.0 | 3.31.0 |
| `agentscope` | 2.0.10 | — |
| `typesafe-sdk` | 0.7.5 | — |
| `httpx` | 0.28.1 | 0.28.1 |
| `httpx2` | — | 2.13.1 |
| `python-dotenv` | 1.2.2 | 1.2.4 |
| `pydantic` | 2.13.4 | 2.14.1 |
| `tokenizers` | 0.23.3 | 0.23.3 |

`tokenizers` was imported from a separate package directory on `PYTHONPATH`; it was not installed in either venv.
A new setup may install that exact version into each venv. The local artifact bundle includes both environments'
distribution metadata, recorded after the experiment. It does not contain credentials or virtualenv binaries.

Token accounting uses `Qwen/Qwen3.5-9B`'s **`tokenizer.json`**, revision
`c202236235762e1c871ad0ccb60c8ee5ba337b9a`, with SHA-256
`5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`.
This is a **budget proxy**, not a claim that Qwen 3.8 uses that tokenizer. Reported downstream inputs use actual API usage.

## Request parameters

| Stage | Sampling/output parameters | Execution limits |
| --- | --- | --- |
| Hermes collection | `max_tokens=1024`; `reasoning_effort=none`, `enable_thinking=false`; no explicit temperature or seed | 12 agent iterations, 240-second run budget; four workers; 360-second subprocess timeout |
| S generation | `temperature=0`, `max_tokens=4096`; thinking disabled; no seed | OpenAI client: 90-second timeout, `max_retries=1` |
| H generation | `temperature=0`; no explicit API `max_tokens`; thinking disabled; no seed | Same 90-second client timeout / one SDK retry; four workers; 600-second subprocess timeout |
| Jev ranking | Binary probability question per evidence unit; batch size 10 | Adapter timeout 45 seconds; `max_retries=2`, retry delay 0.5 seconds |
| Answering | `temperature=0`, `max_tokens=2400`, `response_format={"type":"json_object"}`; thinking disabled; no seed | 90-second client timeout, `max_retries=1`; four concurrent conditions, two sequential answers each |

For direct Qwen calls, thinking is disabled with `reasoning_effort="none"` and
`extra_body={"enable_thinking":false}`. The collection wire request carries `enable_thinking=false` at top level.
H's API output limit is intentionally not its summary-body allowance: acceptance uses the local body-token check.
Captured request bodies are authoritative for the recorded run.

Collection exposes only allowlisted `read_file`; source workspaces are read-only. Automatic compression and micro
compaction are disabled during collection. Memory/context files and background review are skipped. Each worker has an
isolated `HERMES_HOME`, workspace and session DB. See [`hermes_worker.py`](./hermes_worker.py).

## Data, pairing and budgets

- **14 task templates**: one reused synthetic payment trajectory plus 13 actual Hermes executions over read-only
  adaptations of upstream fixtures. Long sources use deterministic original head/matching-line views, not added noise.
- Four primary tasks: `payment`, `checkout_504`, `server_error`, `build_token`. Ten short/query-only controls are separate.
  Assignment is fixed from source length before collection; it is not based on scores.
- Three independently requested summary/ranking pairs per task, two answering calls per condition:
  **14 × 3 × 13 = 546 contexts; 1,092 answers**. Repeated answers are not independent task samples.
- S/H remain byte-identical across their own Top 0–5 conditions. Both mechanisms use identical Jev scores and source units.
  Ranking is task-based, not conditioned on the summary. Select a strict descending-score prefix, break ties by unit ID,
  then render in source order. No threshold, skipping or partial-unit truncation. Actual N is `min(N, available units)`.
- Summary-body allowance: `max(64, min(256, int(0.2 * evidence_tokens)))`. S allows up to three total length-check attempts,
  with word targets `max(12, int(allowance * 0.4 * 0.8**attempt))`.
- H allows up to three total length-check attempts. Its requested budget is
  `max(12, int(allowance * 0.8**attempt))`; appended word limit is `max(18, int(requested_budget * 0.35))`.
  Native Historical Task Snapshot/no-user sentinel and Critical Context are retained; other sections may be omitted.
- The complete-input ceiling is computed before answering from protected prompts, the five largest whole evidence units,
  summary allowance and 96 reserve/framing tokens, then enlarged if serialized S needs more space. It is not one universal
  1,000/2,000-token limit or an equal-length comparison. See [`suite_run.py`](./suite_run.py) for the calculation.
- Original system/task messages are preserved. Final collection reports and internal metadata are excluded. Exams/gold
  never enter collection, summary or decision requests. See [`suite.py`](./suite.py) for exact follow-up construction.

Recorded primary-case budgets below use **final scored rows**, after the format clarification:

| Case | Evidence units | Summary allowance | Complete-input ceiling |
| --- | ---: | ---: | ---: |
| payment | 10 | 256 | 4,496 |
| checkout_504 | 5 | 256 | 5,246 |
| server_error | 41 | 256 | 3,185 |
| build_token | 8 | 256 | 3,859 |

The retained pre-amendment payment `budget.json` says 4,459; its final question requires 37 more tokens. The final
`results.json` rows record 4,496 and govern the scored comparison. Frozen artifacts are preserved rather than rewritten.
Every condition fits its recorded ceiling. All 42 H-only contexts shorten Full; at Top 3–5, each mechanism shortens only
9/12 primary contexts per method. All cases remain scored; mean savings do not imply every case saves tokens.

## Scoring and costs

Each answer returns `{"facts": {...}}`. Field checks require exact recursive types/values, with only payment HTTP-code
order ignored. Missing/malformed/failed planned conditions receive zero. Average fields within answers, answers within
generations, generations within tasks, then tasks equally. Report primary/control cohorts separately.

Answer input includes system/task, compressed history and exam. Standalone-method overhead includes one summary and,
for N > 0, one whole Jev ranking, including recorded retries. Ranking cost is identical across N and both mechanisms;
do not multiply by N or divide by sweep size. Evaluation repeats do not amortize overhead. Report input/output tokens
by model. Total fees use [pricing.json](./pricing.json), checked 2026-10-16: Qwen `qwen3.8-max` China (Beijing)
input **$1.65/M**, output **$4.951/M** ([official rate](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-max));
Jev `jev-1.13.0` input **$0.042/M**, output free ([official rate](https://docs.typesafe.ai/models)).

`total_usd = ((summary_input + answer_input) * 1.65 + (summary_output + answer_output) * 4.951
+ jev_input * 0.042) / 1e6`.
At Top 0 charge summary generation plus one Qwen answer; Top 1–5 add one identical whole Jev ranking
and charge the Qwen answer on the enlarged context. Mean usage is averaged across
the same tasks/generations; fees are computed from unrounded usage. Recorded retries are included. The plotted amount
includes one downstream answer and excludes collection/calibration. Full pays its actual mean answering fee and
no compression preprocessing. Two scoring repeats estimate the cost of one answer; they do not amortize overhead.
These are uncached list-price estimates: cache hits are deliberately charged at the regular input rate for comparison.
No free quotas, promotions, taxes or account-specific adjustments are applied. Prices are a dated snapshot, not an invoice;
no total monetary saving is claimed.

## Reproduction levels and artifact availability

1. **Frozen replay** verifies exact artifact hashes, model requests/responses and all 1,092 grades, with zero API calls.
2. **Frozen-input extension/rerun** uses `suite_fusion` to re-answer H + Top 1–5 with saved trajectories, summaries
   and rankings, retaining the other eight arms. Scores can vary; this command does not re-answer all thirteen arms.
3. **Fresh collection/rerun** uses the pinned Hermes fixtures and the commands in [README.md](./README.md). New agent
   calls can produce different trajectories; this reproduces the protocol rather than identical results.

Public Git contains the experiment code, fixture definitions, rules and curated results. The original payment trajectory,
frozen corpus and wire records are **not committed**. Exact replay requires the local artifact bundle; it is not currently
a public one-command reproduction. Do not substitute another payment trajectory: its expected SHA-256 is
`0f37e6510ffafd920d088452d8719026b00fd4e74f87f7dd1a42a85c8287e6f1`.

The prepared bundle is outside Git:
`/Users/yuli/workspace/trajectory-runs/compaction-dual-summary-reproduction-20261016.tar.gz`.
Its SHA-256 is `40ee93c9117dfe59cf0b4dc8887ba4b2c62fa16f3bc97f2dac6d536343f942a3`.
It contains 3,187 files, a relative-path SHA-256 manifest, environment metadata and `verify.py`.
With ReMe's development environment installed, from the ReMe checkout:

```bash
# Extract outside the repository. Substitute the directory holding the archive.
export REPRO_DIR=/path/outside/repository
shasum -a 256 "$REPRO_DIR/compaction-dual-summary-reproduction-20261016.tar.gz"
tar -xzf "$REPRO_DIR/compaction-dual-summary-reproduction-20261016.tar.gz" -C "$REPRO_DIR"
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" python \
  "$REPRO_DIR/compaction-dual-summary-reproduction-20261016/verify.py"
```

Expected result: **3,187 artifact hashes, 546 contexts and 1,092 grades verified; zero API calls**.
The bundle's `corpus/`, `evaluation/`, `native/`, `native-source/`, `combined/` and `final/` directories correspond to
[README.md's run stages](./README.md). Pass `--native-evaluation <bundle>/native-source` when reusing its H generations.

Fresh runs require `.env` entries `LLM_API_KEY`, `LLM_BASE_URL`, `DECISION_MODEL_API_KEY`, optional
`DECISION_MODEL_BASE_URL`, and `DECISION_MODEL_NAME=jev-1.13.0` to request the recorded Jev version when available.
Use isolated Python environments, the versions above, the pinned Hermes checkout and tokenizer, and new output directories.
Do not commit `.env`, raw records or the bundle. No fresh paid inference is needed for frozen replay.
