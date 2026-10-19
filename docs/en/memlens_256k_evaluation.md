# MemLens-256K Evaluation Notes

These notes accompany the two LLM-Judge charts in the [multimodal memory article](./blog_20261009.md#memlens-256k-results). They describe the main experiment frozen on October 16, 2026; subsequent runner changes and independent reproduction results do not replace its chart values.

## Results and Population {#results}

The evaluation starts with the 195 questions in the official MemLens `agent_subset_195.json` and their complete 256K histories, then applies the six-QID exclusion below. All ten rows cover the same 189 questions. The official category/subtype-specific LLM-Judge protocol assigns a binary 0/1 score per question; percentages are `100 × correct / 189`, displayed to two decimal places.

| Model | Method | Judge correct / 189 | LLM-Judge (%) |
| --- | --- | ---: | ---: |
| Qwen3.6-35B-A3B | Full Context Image | 89 / 189 | 47.09 |
| Qwen3.6-35B-A3B | ReMe Text | 78 / 189 | 41.27 |
| Qwen3.6-35B-A3B | ReMe Image | 101 / 189 | 53.44 |
| Qwen3.6-35B-A3B | OpenViking | 70 / 189 | 37.04 |
| Qwen3.6-35B-A3B | Mem0 | 73 / 189 | 38.62 |
| Qwen3.8-Max | Full Context Image | 124 / 189 | 65.61 |
| Qwen3.8-Max | ReMe Text | 100 / 189 | 52.91 |
| Qwen3.8-Max | ReMe Image | 137 / 189 | 72.49 |
| Qwen3.8-Max | OpenViking | 80 / 189 | 42.33 |
| Qwen3.8-Max | Mem0 | 97 / 189 | 51.32 |

ReMe Image's improvements over Full Context Image use unrounded values: `100 × (101 − 89) / 189 = 6.35` percentage points and `100 × (137 − 124) / 189 = 6.88` percentage points. Valid zero scores and normal empty answers remain in the evaluation; scores do not determine exclusions.

## Method and Judge Settings {#evaluation-settings}

| Method | Memory input and answer-time data access |
| --- | --- |
| Full Context Image | The answer model receives the complete text and original images directly, without building or retrieving memory. |
| ReMe Text | Original text enters Auto Memory; the answer Agent uses BM25 to search daily notes, digest notes and original sessions, then reads relevant text. It does not read images. |
| ReMe Image | Original text and images enter Auto Memory without benchmark-supplied captions. Retrieval covers the same sources as Text; the benchmark plugin's `read_image` bridge can reopen saved original images. |
| OpenViking | Native image descriptions and memory processing; retrieval is restricted to memory with native top 10, not original resources or skills. A JSON parser correction is retained, so this is not unmodified upstream. |
| Mem0 | Mem0 2.0.4 native vision ingests original images with the same candidate model, without benchmark captions; FAISS/top-20 retrieval accesses the generated memories. |

ReMe uses 200,000 / 400,000-token memory/answer context settings, temperature 0 and thinking enabled. Memory/compression and answer output budgets are 65,536 / 16,384 tokens. Each question has an isolated answer Agent with at most 30 iterations and native context compression. Image's `read_image` adapter accesses saved attachments with a 50 MiB read limit and 4,096-image retention. References and question categories/subtypes are supplied only to scoring, not candidate methods.

Full Context, OpenViking and Mem0 also use the respective candidate model for final answering, with temperature 0, thinking enabled and 16,384 output tokens. Their memory stages do not share that budget: Mem0 retains native 2,000-token output and temperature/top_p 0.1 settings; OpenViking uses its native image-description pipeline, with an adaptation that makes image-processing failure explicit rather than treating a missing image as successful ingestion.

All rows use **Qwen3.8-Max** as Judge, with temperature **0**, thinking **disabled** and a **256-token** output budget, isolated from candidate memory applications. “Official protocol” refers to the scoring prompts and parsing rules; the Judge model and parameters are this experiment's configuration, not a claim that the benchmark authors mandate them.

The charts therefore compare these complete system configurations, not an image-toggle ablation under identical retrieval access. They do not establish a cost or speed ranking.

## Common Content-Moderation Filter {#content-moderation-filter}

We take the union of QIDs with an explicit provider content-moderation rejection in ReMe, OpenViking or Mem0 across either model, then apply that identical set to every method and both models, including otherwise successful results on excluded questions. Neither scores nor generic HTTP status codes determine this filter.

The table abbreviates the explicit codes as **A** = `InternalError.Algo.DataInspectionFailed` and **B** = `data_inspection_failed`.

| Excluded QID | Direct supporting observation | Stage | Observed codes |
| --- | --- | --- | --- |
| `q_028cb832` | OpenViking / Max | memory | A + B |
| `q_1d99a36c` | OpenViking / A3B | memory | A + B |
| `q_3b01c02a` | ReMe Text and Image / A3B; OpenViking / A3B and Max; Mem0 / A3B | memory | First four: A + B; Mem0: B |
| `q_564a657b` | ReMe Image / Max | answer | A + B |
| `q_600a79aa` | ReMe Image / Max | memory | A + B |
| `q_c9f8e24d` | ReMe Text / Max | answer | A + B |

Ten direct evidence records support this list. A memory rejection may belong to the historical ingestion attempt reused by the main experiment, rather than a new rejection during a later answer attempt. Ordinary 400/429 responses, generic RuntimeError values, or another method's failure do not prove that a particular method triggered moderation. The original 195 questions and failure evidence are retained; reported results use the remaining **189/195** questions consistently.

## Independent Reproduction Check {#independent-reproduction}

The independent ReMe Image experiment used revision `d3e79918622173306be79ecda6494acadc7c4312`, followed by one bounded technical recovery while preserving original results. After the same filter, A3B / Max cover 188/189 and 187/189 questions. Each pair below uses exactly the same successful QIDs and question/reference inputs; these means are separate from the 189-question main charts.

| Model | Paired questions | Original ReMe Image correct | Independent reproduction correct | Original → reproduction LLM-Judge (%) |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.6-35B-A3B | 188 | 100 | 96 | 53.19 → 51.06 |
| Qwen3.8-Max | 187 | 135 | 134 | 72.19 → 71.66 |

A3B's `q_3714b35c` and Max's `q_2dcbc8f1` and `q_7c14354d` remain incomplete-ingestion technical gaps, not successful results or automatically assigned zero scores. The paired differences are −2.13 / −0.53 percentage points. No repeated stochastic trials or statistical-equivalence test was performed; proximity is not a claim of per-question reproducibility or a causal explanation.

## Pinned Configurations and Sources {#sources}

- Data and protocol: [MemLens dataset](https://huggingface.co/datasets/xiyuRenBill/MEMLENS) and [pinned official evaluation code](https://github.com/xrenaf/MEMLENS/tree/77f3ab9a52fa2d6a17978e2dffe80438a4ecced2).
- Public ReMe implementation: [MemLens runner and setup](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/benchmark/memlens/README.md), [candidate configuration](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/plugins/memlens/src/reme_memlens/benchmark.yaml), [Judge configuration](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/plugins/memlens-judge/src/judge_memlens/plugin.yaml), and [Judge protocol](https://github.com/wang-qisen/ReMe/blob/f89f166dcf8b5b37a4ed9a5e7c3fdbdd042170d8/plugins/memlens-judge/src/judge_memlens/protocol.py). Those directories at this public commit match the independent experiment's `d3e79918`; it is not the revision used for every method in the main experiment.
- The main ReMe/OpenViking benchmark baseline was `a9fa8330e000ca25b7b94a00a64165c0a3a2b8e7`. Full Context answers were originally generated at `16da81cbd7a0594c6e1d080b5c12548ee199fa6c`, then reused through `exp-0007 → exp-1001 → exp-1002`; they were not regenerated at the later baseline revision. The patched native OpenViking revision was `125058ce677e2238eb359ada5b015ee0ff4c4d16`, and the native Mem0 revision was `75a37ec93db7278e3bd9aaf2aa3d6e5139e6789d`. Historical adapters and environments remain in the experiment archive; current main is not substituted for those versions.

The public runner evaluates ReMe Image from a fresh workspace on the original 195 questions by default. The six-QID filter here is a result-analysis step, not an implicit runner filter. Data, dependencies (including Pillow), and external model access must be prepared separately; fresh API calls need not reproduce historical outputs byte for byte. Later dependency, diagnostic or usage-accounting fixes do not retroactively change these results.

### Statistical Source Fingerprints

The [result table](#results) and [exclusion list](#content-moderation-filter) above are public statistical summaries versioned with this document. The numeric source was frozen at `20261016T223731.061980`, with snapshot manifest SHA256 `e2133ee23bdf055c6185c09dd62e4f1ab04f4d6e31caea98080915c7d628694c`. The per-question statistical source has SHA256 `10d5f38705562fbd9f2fdaf591dd1e715959fd5ddaac5c16d9650bf8a24f0da5`; the audit list of ten moderation records has SHA256 `eff2a737908c0b5e6dc1a8e9dbb52dc4c7120f3f3fd927777f138e9aa69ef538`.

Raw questions/answers, images, logs and the full experiment archive are not published with this page. These fingerprints identify archived sources; they do not replace the source records or constitute a complete offline release for all five methods.
