# Fixed summary + selected original evidence

2026-10-16 · Qwen `qwen3.8-max` · Jev `jev-1.13.0` · one original Hermes-collected synthetic payment trajectory.

| Method | Input tokens | Fact accuracy |
| --- | ---: | ---: |
| Full context | 4,715 | 100.0% |
| S | 2,937 | 73.3% |
| S + Jev Top 1 | 3,134 | 72.7% |
| S + Jev Top 2 | 3,247 | 86.0% |
| S + Jev Top 3 | 3,360 | 94.0% |
| S + Jev Top 4 | 3,529 | 100.0% |
| S + Jev Top 5 | 3,585 | 100.0% |

Input tokens are mean actual downstream API usage, including the original system/task and follow-up.
Every method has five valid contexts and 15 answers. All answers pass all six executable repair checks; the table
therefore measures differences in fact retention, not a demonstrated difference in repair success.

**Top 4 matches Full context on the ten checked facts while reducing downstream input by 25.2%.** Adding Top 5
uses more tokens without improving this score. Top 1 does not improve S; Top 2 and Top 3 improve it by 12.7 and
20.7 percentage points. These observations are specific to this task, not statistical equivalence or general superiority.

![Frozen summary plus ranked original evidence](../../docs/figure/compaction-topn-results.svg)

## What is fixed

The [protocol and runnable commands](./README.md) keep one byte-identical summary S and one Jev ranking per generation.
S summarizes all original evidence under a 3,200-token complete-input allowance; fusion appends original blocks without
rewriting S. The extended sweep raises the final complete-input ceiling from 3,600 to **3,800 tokens** before new answer
calls, solely to accommodate Top 5 with its full evidence and budgeting reserve. All compressed API inputs are within
this ceiling (2,924–3,602 tokens). More originals intentionally cost more tokens; lengths are not forced equal.

The source has **10 evidence units, so the maximum is Top 10**. This sweep tests Top 1–5. In the first ranking, Top 3
contains the incident log, retry implementation and payment policy; Top 4 adds `expected_cases.json`, restoring the exact
regression attempt counts that S + Top 3 sometimes loses. Top 5 also retains the README.

There are five frozen summary/ranking pairs and three answers per method: **35 contexts, 105 answers**. Full context,
S and Top 1–2 reuse all 60 answers from the immediately preceding paired run. Top 3–5 add 45 new answers. All five pairs
are retained; no prediction-based filtering, new summaries or new Jev scores enter the extension.

## Gold, audit and scope

The original fixture predates these evaluations. Its oracle contains ten facts: incident, invoice and charge IDs,
amount, ordered idempotency keys, first-attempt commit state, retry limit, non-retryable HTTP codes, original key-generation
line and named regression-test attempt counts. Matching is type-strict and nested; HTTP-code order is ignored. The six
restricted executable checks cover success, timeout retry with a stable key, HTTP 402/422 propagation, three-attempt
exhaustion and independent keys for separate payments. No LLM judge or generated answer key is used.

The source has 11 messages, six tool calls and six complete results, including the actual system prompt. Its final
assistant report is excluded from compression. No synthetic noise or identifier substitutions are added. Source SHA-256:
`0f37e6510ffafd920d088452d8719026b00fd4e74f87f7dd1a42a85c8287e6f1`.

The audit replayed all 105 grades, verified exact retained originals and nested Top-N sets, byte-identical summaries,
protected prompts, original source hash, actual input ceilings and unchanged reused request/response records. No configured
API keys were found. The 45 new Qwen calls use 157,092 input and 9,316 output tokens; existing answers and compression
have additional usage. Downstream input reduction is not a claim about total pipeline cost.

Artifacts stay outside the repository under `trajectory-runs/payment-fixed-summary-topn1to5-20261016/results/`:
`protocol.json`, frozen contexts/selections, exact requests/responses, per-answer results and `audit.json`.
One synthetic task with repeated measurements is not 35 independent tasks. This is direct Qwen evaluation, not Hermes
continuing its agent loop. The earlier length-matched diagnostic also found pure Jev reaching 100% with about 3,251
input tokens on this task, so **this sweep does not establish fusion superiority over pure Jev**. Production
`compact_context` retains its conservative preview/recovery contract; this hybrid remains benchmark-only.
