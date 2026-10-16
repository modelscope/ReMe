# Frozen summary + Jev Top N

One payment trajectory, one fixed-summary experiment, one [results table](./RESULTS.md).
The question is whether adding selected original evidence repairs information lost by a summary.
This benchmark is separate from production `compact_context`.

## Protocol

Hermes collected the synthetic payment investigation: 11 messages with the actual system prompt and six paired tool
calls/results. Exclude the final assistant report, then losslessly group tool results into **10 evidence units**.
Short files remain whole; long logs group correlated events and routine text. No noise or identifier variants are added.
The fixture supplies ten exact facts and six executable repair checks; no LLM creates or judges the gold answers.

For each of five generations, create one summary **S** of all evidence and one Jev ranking using only the initial task
and original evidence. Neither compressor sees the follow-up question or gold. Freeze both before answering:

- **Full context:** original history, allowed to exceed the compressed-input ceiling.
- **S:** the frozen summary.
- **S + Jev Top 1–5:** exactly the same S, plus the first N original units ranked by usefulness.

Select a strict descending score prefix, break ties by unit ID, and restore source order when rendering. There is no
probability threshold, skipping, truncation or summary rewriting. **There are 10 units, so Top 10 is the maximum; the
reported sweep tests Top 1–5.** Larger N requires more input space.

S is generated with a **3,200-token complete-input allowance**. The sweep uses a **3,800-token complete-input ceiling**,
including the same original system/task, evidence, follow-up and framing. This is incremental evidence at extra input
cost, not an equal-length S-versus-fusion comparison. A local Qwen tokenizer and 64-token reserve budget requests;
actual API usage is checked independently. Overruns fail instead of shrinking S or silently dropping original units.

Each context receives three answers: 35 contexts and 105 answers, temperature zero, thinking disabled. Average ten
strict fact checks within each answer, then answers and generations equally. Also report the proportion passing all
six restricted fake-client repair tests. Invalid conditions stay in the denominator with zero credit.
**Hermes collected the source; evaluation calls Qwen directly**, without tool continuation or recovery.

## Run

Use the development environment plus optional `tokenizers`; no Hermes runtime is needed for replay.
The runner accepts only the pinned original payment trajectory whose fixture oracle is in [cases.py](./cases.py).
Credentials come from `.env`: `LLM_API_KEY`, `LLM_BASE_URL`, `DECISION_MODEL_API_KEY`, and optional
`DECISION_MODEL_NAME` / `DECISION_MODEL_BASE_URL`. Provider calls require `--live`.

```bash
python -m benchmark.compaction.run --live \
  --trajectory /path/outside/repository/trajectory.full.json \
  --tokenizer /path/to/cached/qwen/tokenizer.json \
  --output /path/outside/repository/new-evaluation
```

Defaults: `qwen3.8-max`, five generations, three answers, Top 1–5 and four concurrent requests. To use every previously
frozen S/ranking pair without new compression calls, add `--frozen-run /path/to/previous/results`. This generates fresh
answers for every method; `--compressions` must match all saved summary generations. For an offline input reconstruction,
replace `--live` with `--check-only --frozen-run /path/to/previous/results`.

`--top-n` can extend the sweep to at most 10. Increase `--input-cap` explicitly if needed; the runner records over-budget
contexts rather than changing their content. Outputs must be new directories outside the repository. Protocol, source
hashes, frozen selections, code snapshots, requests/responses, usage and per-answer checks remain there.
