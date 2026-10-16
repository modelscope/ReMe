# Matched-input context compaction results

2026-10-16 · `qwen3.8-max` · compressed-input ceiling: **3,300 tokens**.
Full context is an over-budget reference. All other methods share the same complete input ceiling.

| Method | Input tokens | Reduction | Fact accuracy |
| --- | ---: | ---: | ---: |
| Full context | 8,030 | 0.0% | 100.0% |
| Jev | 2,903 | 63.8% | 95.0% |
| Summary | 3,045 | 62.1% | 88.3% |
| Jev + Summary | 3,094 | 61.5% | 90.0% |

Input is mean actual downstream API usage, including the system prompt, task, evidence and evaluation question.
Full requests use 7,480–8,580 tokens; compressed requests use 2,774–3,140. Every method has 12/12 valid contexts
and 24 answers. All methods pass 100% of their task checks, which therefore do not distinguish task performance.

**This run does not support the hypothesis that fusion is best.** Fusion improves fact accuracy over Summary by
1.7 percentage points, but trails Jev by 5 points and Full context by 10. Its 61.5% input reduction does not establish
lower total pipeline cost. The result must not be presented as equivalent to full context or better than both baselines.

## Protocol

- Four methods: original full history; Jev-selected original evidence; Qwen summary; Jev-selected evidence plus a
  complementary Qwen summary. Full retains original tool messages and calls, excluding the final assistant report.
  Compressed methods retain the same original system/task and replace the tool history with an evidence bundle.
- Three variants of each of two synthetic task families: payment retry diagnosis with executable repair checks,
  and replica-lag investigation with structured recovery-plan checks. Variants change identifiers, not underlying
  task structure; these are not six independent real-world tasks. Payment input originates from a Hermes-collected
  synthetic trajectory, with 180 routine log lines added. Replica input is a deterministic fixture.
- Per variant/method: two independent compression generations, two answers per context, temperature zero, thinking
  disabled. All 48 contexts and their 96 answers are newly generated; no baseline answers are reused.
- Fusion retains whole Jev-selected source groups within 40% of the available evidence space, then uses all remaining
  space for a summary of the other evidence. Retained originals are visible to the summarizer to avoid repetition.
  Both selection methods use the same task-usefulness question and a probability threshold of 0.5.
- The ceiling includes the entire answer request. The local Qwen tokenizer counts JSON-serialized messages with
  estimated framing and a 64-token reserve; this is conservative budgeting, not the provider's exact chat tokenizer.
  Actual API usage is checked separately; an overrun invalidates the condition. Equal upper bounds do not force equal
  actual input lengths. Summary generation may retry at most three times for length, using the same policy in both
  summary methods. Evaluation answers cannot affect compression, retries or selection.
- Strict fact scoring compares JSON values and types, including all elements of nested lists/mappings. Means are
  computed within each case, then across cases. Invalid conditions score zero. Payment task checks execute six
  restricted function tests; replica plans receive five structured checks. These are diagnostic checks, not a
  complete agent task success rate. No LLM judge, tools, archive retrieval or Hermes continuation is used for answering.

## What was lost

Jev omitted the payment fixture's exact regression attempt-count mapping in all 12 payment answers.
Summary omitted non-retryable HTTP codes in all 12 and sometimes lost the attempt limit or expected attempt counts.
Fusion also lost policy and test details during summarization: 9 payment answers missed the attempt limit,
10 missed the non-retryable codes, and 5 missed the exact attempt-count mapping. All replica facts were retained by
all four methods. A stronger summary and a different evidence allocation remain hypotheses, not proven improvements.

A completed summary-first development run on the same six variants scored 93.3% for fusion, versus 95.0% for Jev.
The final evidence-first protocol above was frozen before its own calls and also failed to beat Jev. Both runs are
retained outside the repository. The redesign used these same task families; this is development-set evidence,
not held-out validation. Earlier pilot figures and payload-only/append experiments are superseded by this protocol;
their source remains in Git history and their raw artifacts were not deleted.

## Reproduction and audit

See [the runner and command](./README.md). The archived input trajectory is required and is not bundled in the repo.
Source SHA-256: `0f37e6510ffafd920d088452d8719026b00fd4e74f87f7dd1a42a85c8287e6f1`.
Protocol, case variants, grading data, tokenizer hash and code snapshots were saved before inference.
All 96 strict grades were replayed offline. Source spans reconstruct every original observation exactly, selected
snippets match those spans, protected prompts are unchanged, and compressors receive no exam or expected answers.
The source trajectory was unchanged and no configured API keys were found in artifacts.

This final run made 120 Qwen calls (96 answers and 24 summaries): 815,670 input / 31,200 output tokens.
It also made 96 Jev requests: 238,272 input / 16,644 output tokens. These are recorded provider usages for the full
repeated experiment, not per-task billing estimates. No total monetary cost was calculated. Raw responses, contexts,
usage, `results.json`, `REPORT.md`, `validation.json` and independent `audit.json` remain outside the repository under
`compaction-matched-evidence-first-20261016/`; the summary-first development run is `compaction-matched-20261016/`.

Fusion is benchmark-only. The production `compact_context` contract is unchanged.
