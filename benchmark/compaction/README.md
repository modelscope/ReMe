# Matched-input context compaction

One runner, four methods, one table. See [results and protocol](./RESULTS.md).

```bash
python -m benchmark.compaction.run --live \
  --trajectory /path/to/hermes/trajectory.full.json \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/matched-experiment
```

Provider configuration comes from the repository `.env`: `LLM_API_KEY`, `LLM_BASE_URL`, `DECISION_MODEL_API_KEY`,
and optional `DECISION_MODEL_NAME` / `DECISION_MODEL_BASE_URL`. Qwen defaults to `qwen3.8-max`.
The optional `tokenizers` package and a local tokenizer JSON are required only for this benchmark.

- **Full context:** original messages, excluding the final assistant report; allowed to exceed the input limit.
- **Jev:** rank whole source groups by task usefulness and retain original evidence that fits.
- **Summary:** summarize all evidence within the available input space.
- **Jev + Summary:** retain Jev-selected original groups within 40% of the available space, then summarize the
  remaining evidence using all unused input capacity. The summarizer sees retained evidence to avoid duplication.

All compressed methods share the default **3,300-token total input ceiling**, including the unchanged system prompt,
initial task, evidence, evaluation question and message framing. This is an upper bound, not forced equal length.
Budgeting uses a frozen local Qwen tokenizer with a 64-token reserve; actual API input above the ceiling invalidates
that condition. The full context is an over-budget reference, not a deployable choice under this ceiling.

The corpus contains three deterministic variants of a long payment investigation and three of a replica investigation.
Payment evidence originates from a Hermes-collected synthetic trajectory, with routine logs added. Replica evidence
is a synthetic fixture. Variants change identifiers; they are not six independent real-world tasks. Every full history
must exceed the ceiling. The fixed defaults generate each compression twice and answer each context twice: 48 contexts,
96 answers. Selection and summarization receive the task and source, never evaluation questions or expected answers.

Fact scoring is strict JSON equality, including types. Payment fixes run six restricted, deterministic function tests;
replica plans receive five structured checks. The table averages within each case and then across cases; failed
conditions contribute zero. These checks do not measure a complete agent run. Evaluation calls Qwen directly;
Hermes does not continue its agent loop, and no method retrieves discarded evidence.

All conditions, source variants, expected answers, tokenizer hash and code are saved before inference. Summary budget
retries are limited to three attempts, using the same policy for both summary methods; they cannot inspect evaluation
answers. Runtime artifacts stay outside the repository: `protocol.json`, `*.source.json`, exact requests/responses,
contexts, `results.json`, `aggregate.json`, `REPORT.md` and `validation.json`. Outputs never overwrite earlier runs.
Input reduction in the table concerns downstream answering requests; compression has additional provider usage.
