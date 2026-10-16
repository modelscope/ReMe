"""Freeze public gold-labelled questions, then collect each trajectory through Hermes Agent."""

import argparse
import asyncio
import hashlib
from pathlib import Path
import subprocess

from benchmark.compaction.cases import choose, fixture, load_questions, write


async def run(args):
    """Freeze the complete corpus before any model calls; run finite isolated Hermes workers."""
    repo = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output.exists() or output == repo or repo in output.parents:
        raise ValueError("Use a new output directory outside the repository")
    questions = choose(load_questions(args.dataset), args.count, args.seed)
    revision = subprocess.check_output(["git", "-C", str(args.hermes), "rev-parse", "HEAD"], text=True).strip()
    output.mkdir(parents=True)
    manifest = {
        "dataset": "HotpotQA distractor validation",
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "source": "https://huggingface.co/datasets/hotpotqa/hotpot_qa",
        "license": "CC BY-SA 4.0",
        "seed": args.seed,
        "count": args.count,
        "hermes_commit": revision,
        "model": args.model,
        "sampling": "Hash order; balanced bridge/comparison; 10 article-disjoint contexts; 6k-32k source characters",
        "questions": questions,
    }
    write(output / "corpus.json", manifest)
    for name in ("collect.py", "hermes_worker.py", "cases.py"):
        (output / name).write_bytes((Path(__file__).parent / name).read_bytes())
    for row in questions:
        root = output / row["_id"]
        work = root / "workspace"
        work.mkdir(parents=True)
        prompt, files = fixture(row)
        for name, text in files.items():
            (work / name).write_text(text)
        write(
            root / "collection-task.json",
            {
                "prompt": prompt,
                "model": args.model,
                "source_hashes": {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()},
            },
        )
    semaphore = asyncio.Semaphore(args.concurrency)
    failures = []

    async def collect(row):
        root = output / row["_id"]
        async with semaphore:
            with (root / "worker.log").open("w") as log:
                process = await asyncio.create_subprocess_exec(
                    str(args.hermes_python),
                    "-m",
                    "benchmark.compaction.hermes_worker",
                    "--root",
                    str(root),
                    "--hermes",
                    str(args.hermes),
                    "--env-file",
                    str(repo / ".env"),
                    cwd=repo,
                    stdout=log,
                    stderr=log,
                )
                try:
                    code = await asyncio.wait_for(process.wait(), 360)
                except BaseException:
                    if process.returncode is None:
                        process.terminate()
                        try:
                            await asyncio.wait_for(process.wait(), 10)
                        except asyncio.TimeoutError:
                            process.kill()
                            await process.wait()
                    raise
            if code:
                failures.append(row["_id"])
                print(row["_id"], "FAILED", flush=True)
            else:
                print(row["_id"], "collected", flush=True)

    async with asyncio.TaskGroup() as tasks:
        for row in questions:
            tasks.create_task(collect(row))
    write(
        output / "collection-status.json",
        {
            "planned": len(questions),
            "completed": len(questions) - len(failures),
            "failed": failures,
        },
    )
    if failures:
        raise RuntimeError("Collection failures remain in the frozen corpus; inspect worker logs")
    print("CORPUS", output / "corpus.json", flush=True)


def main():
    """Use an explicit Hermes checkout/interpreter; keep collection separate from scored evaluation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--hermes", type=Path, required=True)
    parser.add_argument("--hermes-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--model", default="qwen3.8-max")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live or args.concurrency < 1:
        parser.error("Use --live and positive concurrency; provider calls incur charges")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
