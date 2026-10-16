# Fixed-summary compaction on fourteen fixture tasks

2026-10-16 · Qwen `qwen3.8-max` · Jev `jev-1.13.0` · **14 distinct queries with predefined answers**.
Four source-length-qualified tasks form the primary cohort; ten short/query-only controls are reported separately.
Cohorts were fixed before collection, with no accuracy-based task filtering.

## Primary cohort: four tasks

| Method | Mean input tokens | Fact score | Valid contexts |
| --- | ---: | ---: | --- |
| Full context | 4,014 | 100.0% | 12/12 |
| S | 2,480 | 82.0% | 12/12 |
| Hermes small-window adapter | 2,432 | 79.4% | 12/12 |
| S + Jev Top 1 | 2,753 | 83.0% | 12/12 |
| S + Jev Top 2 | 2,974 | 94.5% | 12/12 |
| S + Jev Top 3 | 3,241 | 99.5% | 12/12 |
| S + Jev Top 4 | 3,496 | 98.1% | 12/12 |
| S + Jev Top 5 | 3,660 | 97.4% | 12/12 |

Input tokens are actual downstream API usage, including the original system/task and follow-up. Fact score averages
strict JSON field checks within each answer, then generations and tasks equally; invalid conditions score zero.
Full context reaches 100%; S + Top 3 reaches **99.5% with 19.3% less downstream input** (3,241 versus 4,014 tokens).
Top 4 and Top 5 do not improve this point estimate. No equivalence test or general optimal-N claim is made.

![Primary-cohort input and fact score](../../docs/figure/compaction-topn-results.svg)

## What was tested

The [full query/answer table and protocol](./STUDY.md) define the oracle before collection. The four primary tasks are
payment retry investigation, checkout 504 analysis, server-error localization and a build-output token lookup.
The ten controls cover shorter configuration, code, dependency, notes, version and file-generation questions.
All fourteen sources are synthetic fixtures: one existing payment trajectory plus thirteen genuine Hermes executions
over explicitly read-only adaptations of upstream tasks. Long-file views are deterministic original excerpts, not
added noise. These are not the maintainers' private production transcripts.

Each task has three frozen summary/ranking pairs and two answers per method: **336 contexts and 672 answers** across
eight methods. S summarizes every source unit once. Each S + Top N preserves that S byte-for-byte and adds complete
original units, ranked without a threshold and restored to source order. Actual N saturates at the available unit count.
The original payment source has ten units, so its maximum is Top 10; the sweep tests Top 1–5.

S's evidence allowance is 20% of rendered-evidence tokens, clamped to 64–256 local Qwen tokens. A per-task complete-input
ceiling is calculated from protected prompts, the summary allowance, the five largest whole units and reserve, before
scored answers. This permits the incremental sweep; **it is not an equal-length S-versus-fusion comparison or a claim
that every Full input exceeds its ceiling**. All actual inputs are checked. Short cases may gain no token savings.

The added **Hermes small-window adapter** calls the real native generator, with its legacy template, an overridden
64–256-token body budget and an appended total word limit. It retains native redaction/provenance checks and strips
only the native control prefix before the common summary carrier. It bypasses automatic triggering and full-compressor
head/tail selection: **this is a forced simulation, not the unchanged default Hermes compressor**. All **42/42** native
contexts fit their body/input budgets and use fewer actual API input tokens than the corresponding Full context.
No original-history fallback is accepted.

Hermes collects the trajectories; answering calls Qwen directly. Gold and follow-up questions never enter collection,
summary or decision requests. The final collection report is excluded from every history. There is no tool continuation,
retrieval, LLM judge or generated answer key. Exact string/type compliance is part of this metric; it does not by itself
prove semantic information loss or task-completion differences. The native and S methods have the same maximum body
allowance, but their actual lengths differ. Four primary templates are too few to establish general superiority.

<details>
<summary>Ten short/query-only controls</summary>

| Method | Mean input tokens | Fact score | Valid contexts |
| --- | ---: | ---: | --- |
| Full context | 2,727 | 100.0% | 30/30 |
| S | 2,315 | 67.1% | 30/30 |
| Hermes small-window adapter | 2,308 | 73.2% | 30/30 |
| S + Jev Top 1 | 2,493 | 84.7% | 30/30 |
| S + Jev Top 2 | 2,573 | 87.5% | 30/30 |
| S + Jev Top 3 | 2,687 | 92.9% | 30/30 |
| S + Jev Top 4 | 2,722 | 92.9% | 30/30 |
| S + Jev Top 5 | 2,722 | 92.5% | 30/30 |

All controls remain in their separate denominator. They are not presented as ten additional long-context tasks.

</details>

## Audit and reproducibility

See [commands](./README.md). The audit replayed all **672** grades, reconstructed original source spans, verified source
hashes and actual initial system prompts, checked frozen S and strict nested Top-N sets, protected prompts, question/gold
isolation, actual token ceilings, native strict shrinkage and configured-key exclusion. All 336 contexts are valid.

The format preflight exposed two underspecified answer shapes: payment counts as arrays and note text with bullet
markers. Those two follow-ups were clarified without changing gold or graders, and every seven-arm condition on both
tasks was re-answered using the same S/rankings. Their 84 initial answers remain archived and excluded; all 504 answers
from the other twelve tasks remain included. The native adapter adds 84 fresh answers. Unadapted native/length-only
calibration attempts are also retained; they are not silently counted as successful compression.

Formal recorded usage: **757 Qwen calls** (672 answers, 42 S calls, 43 native calls including one length retry),
2,027,184 input / 40,099 output tokens; **54 Jev calls**, 77,799 input / 5,634 output tokens. This excludes Hermes
collection and preflights, including interrupted calibration attempts. No complete monetary-cost claim is made.
Downstream input reduction is not total pipeline savings or a prompt-cache measurement.

Artifacts remain outside the repository: `hermes-fixture14-20261016/` holds the frozen corpus and actual Hermes sessions;
`compaction-fixture14-20261016-v2/` holds the seven-arm records; `compaction-fixture14-hermes-adapted-20261016/` holds native
generation; `compaction-fixture14-final-20261016/` holds the combined results and `audit.json`. This is a development panel,
including a previously used payment task, not independent held-out confirmation. Production `compact_context` is unchanged.
