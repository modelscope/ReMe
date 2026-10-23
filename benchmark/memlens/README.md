# ReMe Image on MemLens-128K / 256K

Evaluate ReMe Image on MemLens's official 195-question memory-agent subset.
Each length uses its own full histories; every question has an isolated workspace.

## Run

```bash
pip install -e ".[as]" -e plugins/memlens -e plugins/memlens-judge
export MEMLENS_DATA=/path/to/MEMLENS
export EXPERIMENT_DIR=/path/to/new-experiment
python -m benchmark.memlens.run --model qwen3.8-max --context-length 256k
```

Supply `LLM_API_KEY` and `LLM_BASE_URL` through the environment, outside Git.
The dataset directory contains `dataset_128k.json`, `dataset_256k.json`,
`agent_subset_195.json` and `release_images/`. Select 128K with
`--context-length 128k`; `--limit-scenes 1 --output /path/to/separate-experiment`
runs one complete history. Concurrency is configured in `config.yaml`.

## Evaluation

Original text, timestamps, Image IDs and interleaved image bytes go to native
Auto Memory. Supplied BLIP captions and answer annotations are not inputs.
BM25 indexes daily notes, digest notes and original session transcripts.
Each question starts a fresh 30-iteration Agent with `search`, `read` and
`read_image`; no embedding or auto-tagging is used.

| Setting | Memory / compression | Answer |
| --- | --- | --- |
| Model | Selected candidate | Same candidate |
| Thinking / temperature / streaming | On / 0 / off | On / 0 / off |
| Output budget | 65,536 | 16,384 |
| Model context size | 200,000 | 400,000 |

The [candidate preset](../../plugins/memlens/src/reme_memlens/benchmark.yaml)
retains 30 Agent iterations, context trigger/reserve ratios 0.8/0.1, a
50,000-token tool-result limit and 4,096-image retention. Native requests use
three retries, a 60-second delay and a 600-second HTTP timeout; nested retries
are disabled. The runner does not repair model outputs.

The independent [MemLens Judge](../../plugins/memlens-judge/README.md) uses the
official category/subtype-specific binary accuracy protocol, Qwen3.8-Max,
thinking off, temperature 0 and 256 output tokens. SubEM and F1 follow the
official code. Reference answers, question categories and subtypes enter only scoring.

## Results

`<output>/memlens-<length>/<model>/` contains settings and summary JSON.
`reme_image/scenes/<scene>/` retains ingestion responses, a native workspace,
answers, judgments, metrics and coverage status. The workspace's `mem_session/`
contains native Agent JSONL trajectories. Existing output groups are not overwritten.

Usage includes successful memory/answer requests and compression, excluding
Judge costs and failed attempts. Missing cache/reasoning counters remain unknown.
Technical failures are coverage gaps; valid empty or iteration-limit answers are scored.

## Sources and license

[Dataset](https://huggingface.co/datasets/xiyuRenBill/MEMLENS);
[official code](https://github.com/xrenaf/MEMLENS/tree/77f3ab9a52fa2d6a17978e2dffe80438a4ecced2).
The dataset retains its own data/image terms. Adapted query and metric code carries
the following upstream notice:

```text
MIT License

Copyright (c) 2026 Xiyu Ren, Zhaowei Wang, and the MemLens Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
