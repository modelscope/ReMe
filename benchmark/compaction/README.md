# Gold-labelled context compaction benchmark

One corpus, one four-method evaluation, one results table. See [measured results](./RESULTS.md).

The input is the public **HotpotQA distractor validation** split: 7,405 questions with human answers and sentence-level
supporting facts. Source: [HotpotQA](https://hotpotqa.github.io/), [author-maintained dataset](https://huggingface.co/datasets/hotpotqa/hotpot_qa).
Data is CC BY-SA 4.0. Dataset files and runtime artifacts stay outside this repository.

## Run

Use ReMe's development environment plus optional `tokenizers` and, for Parquet input, `pyarrow`. Hermes runs in its own
installed environment. Provider credentials come from ReMe's `.env`: `LLM_API_KEY`, `LLM_BASE_URL`,
`DECISION_MODEL_API_KEY`, and optional `DECISION_MODEL_NAME` / `DECISION_MODEL_BASE_URL`.

Download the validation Parquet from the pinned author revision:

```bash
curl -L 'https://huggingface.co/datasets/hotpotqa/hotpot_qa/resolve/1908d6afbbead072334abe2965f91bd2709910ab/distractor/validation-00000-of-00001.parquet' \
  -o /path/outside/repository/hotpot-validation.parquet

python -m benchmark.compaction.collect --live \
  --dataset /path/outside/repository/hotpot-validation.parquet \
  --hermes /path/to/hermes-agent \
  --hermes-python /path/to/hermes-environment/bin/python \
  --output /path/outside/repository/hermes-corpus

python -m benchmark.compaction.run --live \
  --corpus /path/outside/repository/hermes-corpus/corpus.json \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/evaluation
```

Official-release JSON input is also accepted. Defaults use `qwen3.8-max`, 30 questions, collection seed `20261016`,
and four concurrent provider requests. Each question/method has two compression generations and two answers:
240 contexts and 480 scored answers. Both commands require live opt-in and a new output directory.

## Frozen protocol

Select 15 bridge and 15 comparison questions by seeded SHA-256 order, requiring ten distinct articles per question,
6,000–32,000 original evidence characters, valid supporting references, and no article shared between selected questions.
These structural filters run before model calls; no model score affects eligibility. They are 30 distinct public questions,
not renamed variants of one task. The sample is a filtered subset, not a representative full-dataset score.

Hermes reads all ten evidence files through its actual `read_file` tool. Gold answers and support labels remain outside
the tool workspace. Collection checks every article was read without truncation, all tool calls are paired, files are
unchanged, and the actual initial system prompt is present. Sessions, wire bodies and source hashes are retained.
Automatic compaction and thinking are disabled during collection. Internal Hermes DB fields and reasoning metadata are
removed when projecting the trajectory to public chat fields. The final assistant answer is excluded from evaluation.

- **Full context:** uncompressed public chat history, explicitly allowed to exceed the compressed-input ceiling.
- **Jev:** rank original sentence groups by task usefulness, then retain whole groups that fit.
- **Summary:** summarize all source evidence within the available input space.
- **Jev + Summary:** retain Jev-selected groups within 40% of available evidence space, then summarize remaining
  evidence using all unused space. The summarizer sees retained evidence to avoid repetition.

Every compressed method shares a **3,600-token complete answer-input ceiling**, including original system/task,
evidence, evaluation question and framing. Local budgeting uses a frozen Qwen tokenizer, serialized public messages
and a 64-token reserve. Actual API input is checked separately; overruns invalidate the condition. An upper bound does
not force equal actual lengths. Summary length retries are capped at three and cannot inspect evaluation answers.
Selection and summary requests never receive gold answers or support labels. No method retrieves discarded evidence.

## Scoring and scope

The primary metric is the official answer **Exact Match (EM)** after case/punctuation/article/whitespace normalization.
Answer F1, supporting-fact EM/F1 and joint EM/F1 are separate secondary metrics; they do not replace the primary metric
when results are unfavorable. Supporting facts use exact article titles and original zero-based sentence IDs; malformed
IDs such as booleans, decimal numbers or strings receive no supporting-fact credit. Scoring uses no LLM judge.

Average repeated answers within each question, then average questions equally. Failed conditions stay in the denominator
with zero scores. Report valid/planned counts and actual downstream API input usage. Compression has additional provider
usage, so downstream input reduction is not a claim about total billing cost. The predeclared practical hypothesis is that
fusion exceeds both compressed baselines in answer EM and is within five percentage points of Full context. This margin
is descriptive, not a statistical equivalence test.

**Hermes collects trajectories; evaluation calls Qwen directly.** This is evidence-grounded QA after compaction,
not Hermes continuing a tool-using task. Public questions may be present in model training; supporting-fact metrics help
inspect grounding but do not eliminate contamination. Results cannot establish general agent-task success.

Artifacts include the frozen `corpus.json`, collection records, `protocol.json`, source cases/code, requests/responses,
contexts, `results.json`, `aggregate.json`, `REPORT.md` and validation records. Existing runs are never overwritten.
