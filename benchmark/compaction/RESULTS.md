# Jev across two summary strategies

2026-10-16 · Qwen `qwen3.8-max` · Jev `jev-1.13.0`.

One **13-method experiment**: Full context, generic summary **S + Top 0–5**, and Hermes compaction summary (small-budget setting)
**H + Top 0–5**. Top 0 means summary only. Both curves share the same original evidence and frozen Jev rankings;
each summary remains byte-identical across its six conditions.

## Four primary tasks

| Method | Fact score | Answer input | Summary in / out | Jev in / out |
| --- | ---: | ---: | ---: | ---: |
| Full context | 100.0% | 4,014 | 0 / 0 | 0 / 0 |
| S | 82.0% | 2,480 | 5,379 / 200 | 0 / 0 |
| S + Jev Top 1 | 83.0% | 2,753 | 5,379 / 200 | 4,162 / 344 |
| S + Jev Top 2 | 94.5% | 2,974 | 5,379 / 200 | 4,162 / 344 |
| S + Jev Top 3 | 99.5% | 3,241 | 5,379 / 200 | 4,162 / 344 |
| S + Jev Top 4 | 98.1% | 3,496 | 5,379 / 200 | 4,162 / 344 |
| S + Jev Top 5 | 97.4% | 3,660 | 5,379 / 200 | 4,162 / 344 |
| H (Hermes, small budget) | 79.4% | 2,432 | 3,120 / 152 | 0 / 0 |
| H + Jev Top 1 | 85.3% | 2,705 | 3,120 / 152 | 4,162 / 344 |
| H + Jev Top 2 | 92.9% | 2,927 | 3,120 / 152 | 4,162 / 344 |
| H + Jev Top 3 | 97.9% | 3,193 | 3,120 / 152 | 4,162 / 344 |
| H + Jev Top 4 | 96.9% | 3,448 | 3,120 / 152 | 4,162 / 344 |
| H + Jev Top 5 | 96.9% | 3,613 | 3,120 / 152 | 4,162 / 344 |

![Quality, downstream input and compression overhead](../../docs/figure/compaction-topn-results.svg)

Both summary mechanisms benefit on this panel: S rises from **82.0% to 99.5%** at Top 3; H rises from **79.4% to 97.9%**.
Mean downstream inputs at Top 3 are **3,241 / 3,193**, versus Full's **4,014**: reductions of **19.3% / 20.4%**.
Top 4–5 do not improve these point estimates. This is an exploratory result on four synthetic task templates,
not a general optimal-N claim, equivalence test or proof that Jev beats other equal-budget selectors.

## Token and cost accounting

All table values are mean provider tokens. Answer input includes the original system/task, summary/evidence and held-out
question. Summary and Jev columns are **one-time overhead per standalone condition**, including recorded length retries.
One frozen Jev ranking serves every N and either summary mechanism: Top 1–5 therefore have the same ranking cost;
it is neither multiplied by N nor divided by the number of sweep conditions. Summary-only and Full incur no Jev cost.
The two scoring repeats estimate one downstream answer; overhead is not amortized across those evaluation repeats.

These are token counts, **not currency**: model prices and cached-token discounts are not applied. Compression increases
one-off provider work here; lower downstream input alone does not demonstrate lower total cost. Repeated future turns
may amortize overhead, but that has not been measured.

## Setup and boundaries

[Queries, fixed answers and scoring rules](./STUDY.md) · [Experiment settings and reproducibility](./SETTINGS.md) · [Run commands](./README.md).

The panel contains **14 task templates**, one existing payment trajectory and thirteen real read-only Hermes executions
over synthetic upstream fixtures. Four primary tasks were selected by source length before collection; ten short/query-only
controls remain separate. Three summary/ranking pairs and two answers per condition give **546 contexts / 1,092 answers**.
The extension reused all 42 H summaries, rankings and 672 previous answers; it added only 420 answering calls.
No new summary or Jev calls were needed. All 1,092 grades were replayed against captured requests/responses.

Scoring uses predefined, recursive type-strict JSON field rules, with no LLM judge. Questions/gold/final collection reports
are excluded from summary and decision inputs. Answering calls Qwen directly, without Hermes tool continuation or recovery.
S and H share a 64–256-token maximum summary-body allowance, but use different prompts and actual lengths.
H reuses Hermes' context-compaction summary-generation pipeline with `tail_mode=legacy`, a smaller summary budget
and additional length constraints. It invokes the generator directly, bypassing automatic triggering and head/tail selection. All 42 H-only contexts strictly shorten Full, without original-history fallback.

Top N adds complete source units without truncation, saturating at the available count. The payment source has ten units
(maximum Top 10); this experiment sweeps Top 1–5. Existing per-task input ceilings are preserved, not tuned after answers.
The comparison is incremental, **not equal-length**. All conditions fit their ceilings, but only **9/12 primary contexts
per method at Top 3–5** are shorter than their paired Full. Across the new H fusion arms, 172/210 contexts shorten Full;
the other 38 comprise 9 primary and 29 control contexts. All remain scored. Average savings do not imply per-case savings.

<details>
<summary>Ten short/query-only controls</summary>

| Method | Fact score | Answer input | Summary in / out | Jev in / out |
| --- | ---: | ---: | ---: | ---: |
| Full context | 100.0% | 2,727 | 0 / 0 | 0 / 0 |
| S | 67.1% | 2,315 | 1,099 / 74 | 0 / 0 |
| S + Jev Top 1 | 84.7% | 2,493 | 1,099 / 74 | 929 / 50 |
| S + Jev Top 2 | 87.5% | 2,573 | 1,099 / 74 | 929 / 50 |
| S + Jev Top 3 | 92.9% | 2,687 | 1,099 / 74 | 929 / 50 |
| S + Jev Top 4 | 92.9% | 2,722 | 1,099 / 74 | 929 / 50 |
| S + Jev Top 5 | 92.5% | 2,722 | 1,099 / 74 | 929 / 50 |
| H (Hermes, small budget) | 73.2% | 2,308 | 1,944 / 69 | 0 / 0 |
| H + Jev Top 1 | 80.1% | 2,486 | 1,944 / 69 | 929 / 50 |
| H + Jev Top 2 | 92.5% | 2,566 | 1,944 / 69 | 929 / 50 |
| H + Jev Top 3 | 99.2% | 2,680 | 1,944 / 69 | 929 / 50 |
| H + Jev Top 4 | 99.2% | 2,715 | 1,944 / 69 | 929 / 50 |
| H + Jev Top 5 | 98.8% | 2,715 | 1,944 / 69 | 929 / 50 |

These controls are not ten additional long-context tasks. Their small source-unit counts can make Top N saturate.

</details>

<details>
<summary>Audit and artifact locations</summary>

The audit verifies source hashes, frozen S/H, identical nested Top-N originals, exact captured inputs, all 1,092 grades,
actual token ceilings, unchanged prior results and configured-key exclusion. All 546 conditions are valid.
Prior answer-format amendments and native calibration disclosures are retained in [the protocol](./STUDY.md).

Artifacts under `/Users/yuli/workspace/trajectory-runs/` remain outside Git:
`hermes-fixture14-20261016/` (corpus), `compaction-fixture14-20261016-v2/` (S/rankings),
`compaction-fixture14-hermes-adapted-20261016/` (H), `compaction-fixture14-final-20261016/` (original eight arms),
and `compaction-fixture14-dual-summary-20261016/` (current 13-arm results, usage and audit).
The extension used **1,170,946 input / 19,990 output Qwen tokens** for its 420 answers, with zero new Jev/summary calls.
Historical collection, calibration and complete monetary billing are not included in this incremental usage figure.

</details>
