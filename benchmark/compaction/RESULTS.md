# Gold-labelled context compaction results

2026-10-16 · `qwen3.8-max` · Jev `jev-1.13.0` · compressed-input ceiling: **3,600 tokens**.
**30 distinct public HotpotQA questions with human gold**, collected through Hermes Agent.

| Method | Input tokens | Reduction | Answer EM |
| --- | ---: | ---: | ---: |
| Full context | 5,482 | 0.0% | 61.7% |
| Jev | 2,606 | 52.5% | 51.7% |
| Summary | 2,686 | 51.0% | 61.7% |
| Jev + Summary | 3,043 | 44.5% | 60.0% |

Input tokens are mean actual downstream API usage, including system/task, evidence and the evaluation question.
All methods have 60/60 valid contexts and 120 answers. The independent sample count is 30 questions, not 480 answers.
Full context uses 5,058–6,341 tokens and is an explicitly over-budget reference. Every compressed request is within
the ceiling: actual inputs range from 2,392 to 3,447 tokens. Upper bounds do not force equal actual input lengths.

**The predeclared hypothesis is not met.** Fusion is 1.7 percentage points below Full context and reduces downstream
input by 44.5%, but does not beat Summary: their answer EMs are 60.0% and 61.7%. Summary matches Full context in aggregate
answer EM with less input than fusion. Jev trails both. Close point estimates are not statistical equivalence or
proof of general task performance. Full context is a reference, not a guaranteed per-question oracle.

## Data and protocol

Source: [HotpotQA](https://hotpotqa.github.io/),
[author-maintained validation split](https://huggingface.co/datasets/hotpotqa/hotpot_qa/tree/1908d6afbbead072334abe2965f91bd2709910ab/distractor).
The source contains 7,405 original validation questions, with human answers and supporting sentence annotations,
under CC BY-SA 4.0. This is newly collected Hermes execution over public QA tasks, not the Hermes maintainers' private
session corpus and not an official full-dataset leaderboard evaluation.

Before model calls, select 15 bridge and 15 comparison questions by SHA-256 order with seed `20261016`.
Structural eligibility requires ten distinct articles per question, 6,000–32,000 original evidence characters,
valid support references and no article shared between selected questions. The 30 questions use 300 distinct articles.
No identifier substitution, generated gold, score-based task filtering or synthetic noise is used. The filtered subset
is not a representative random sample of the full validation split.

Hermes commit `30463589eb54fa0f48724594cc0e98e6b995729b` reads all ten article files per question with actual `read_file`
calls: 30 completed trajectories and 300 paired tool calls/results. Every article is read without truncation and
fixture hashes remain unchanged. The actual initial system prompt is retained and matches captured wire requests.
Gold answers and support labels are outside the tool workspace. Final assistant answers are excluded from evaluation.
Only public chat fields are passed to the answering model; Hermes database snapshots and internal reasoning metadata
are stripped. Source transcripts, sessions and raw wire bodies remain archived unchanged.

The four methods share the same original system/task and evaluation question. Full context retains the original
public chat history; compressed methods replace tool history with an evidence bundle. Jev ranks whole original
sentence groups using task usefulness and a 0.5 threshold. Summary summarizes all source evidence. Fusion first retains
Jev-selected originals within 40% of available evidence space, then summarizes the remaining evidence using all unused
capacity; the summarizer also sees retained originals to avoid repetition. Allocation is frozen from earlier synthetic
development, with no HotpotQA answer-based tuning.

The 3,600-token ceiling covers the complete answering request. Budgeting uses a local Qwen tokenizer on serialized
public messages with estimated framing and a 64-token reserve. Actual API usage is checked independently; overruns
score zero. Summary length retries are limited to three and cannot consult evaluation answers. All 240 contexts and
480 answers are generated in this complete run: two compression generations per question/method, two answers per
context, temperature zero, thinking disabled. No baseline answers are reused and no task is removed after scoring.

## Scoring and interpretation

The primary metric is the [official answer Exact Match](https://github.com/hotpotqa/hotpot/blob/master/hotpot_evaluate_v1.py),
using case, ASCII punctuation, article and whitespace normalization. Answer F1 and supporting/joint metrics are
secondary. Supporting facts use exact original titles and zero-based sentence IDs. Malformed citation types receive
no support credit. No LLM creates gold or judges correctness. Repeated answers are averaged within each question,
then questions receive equal weight. Failed conditions stay in the denominator with zero scores.

Secondary metrics, in **Full / Jev / Summary / Fusion** order:

- Answer F1: **72.5% / 60.8% / 77.0% / 71.4%**.
- Supporting-fact F1: **83.0% / 67.2% / 75.5% / 80.0%**.
- Joint EM (answer and exact supporting set): **31.7% / 25.8% / 33.3% / 32.5%**.

Fusion retains supporting facts better than Summary by this secondary F1, but this does not replace the primary
answer metric or establish superiority. Paired question-level answer EM versus Jev: 5 improvements, 23 ties,
2 regressions; versus Summary: 1 improvement, 26 ties, 3 regressions. Fusion is close to Full context on average,
but differs on individual questions: 4 improvements, 23 ties, 3 regressions.

EM is sensitive to answer phrasing. For example, Full context returns `National Football Conference (NFC) West division`
where gold is `National Football Conference (NFC) West`, and gives a full explanation where gold is
`drawing the name out of a hat`; these fail exact matching despite substantial semantic overlap. Another full-context
answer names `Graduation` where the annotated answer is `My Beautiful Dark Twisted Fantasy`. Original predictions are
not rewritten, aliases are not added after scoring, and all six metrics remain available in `aggregate.json`.

Public QA questions may be in model training. Supporting-fact metrics inspect grounding but do not eliminate this
limitation. **Hermes collects the history; evaluation calls Qwen directly**, without continuing Hermes' agent loop,
executing tools or recovering discarded evidence. These results do not measure complete agent-task success.

## Reproduction and audit

See [commands and implementation](./README.md). Corpus IDs, human gold, source hashes, sampler settings and collector
code are frozen in `corpus.json` before collection. Evaluation settings, all source cases and code are frozen before
scored answering. Source dataset SHA-256:
`c20b638ca82b21d04fe12e14ff417ad05153d4d215a65de54497fca4e972f7c6`.

All 480 predictions were replayed against the independently downloaded official evaluator: answer, supporting-fact
and joint metrics match, with no malformed predictions. The audit also reconstructed every source character range,
verified selected originals and their probabilities, checked source/fixture hashes and protected prompts, confirmed
public-field projection and that no exam/gold labels entered compressors, and checked actual input ceilings.
No configured API keys were found in collection or evaluation artifacts.

The formal evaluation records 600 Qwen calls (480 answers, 120 summaries): 2,729,978 input / 63,796 output tokens;
836 Jev calls: 1,520,496 input / 166,300 output tokens. These counts exclude Hermes collection and an interrupted
instrumentation preflight. Downstream token reduction is not total pipeline savings; no total monetary cost was computed.
The preflight was stopped after discovering internal DB snapshots in exported messages; its 87 completed contexts
are retained but excluded. The public-field projection was fixed, then all four methods on all 30 questions were rerun.
No question or prediction was selected based on its score.

Artifacts remain outside the repo: `hermes-hotpot30-20261016/` contains the corpus and real Hermes sessions;
`compaction-hotpot30-20261016-v2/` contains protocol, exact requests/responses, contexts, results, usage and independent
`audit.json`. Earlier synthetic pilots are superseded; their code remains in Git history and raw artifacts were retained.
The hybrid strategy is benchmark-only; production `compact_context` is unchanged.
