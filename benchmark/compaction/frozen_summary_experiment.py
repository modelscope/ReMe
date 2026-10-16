"""Diagnostic ablation: preserve the exact same summary, then append original evidence."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import statistics

from dotenv import dotenv_values
from openai import AsyncOpenAI

from benchmark.compaction.hybrid_cases import pack, render
from benchmark.compaction.hybrid_experiment import Experiment, aggregate, compose
from benchmark.compaction.run import write


def frozen_base(primary, case_name, repetition, budget=600):
    """Reject any change to the baseline summary bytes or its protected context."""
    label = f"{case_name}.c{repetition}.summary.{budget}"
    response = json.loads((primary / f"{label}.summary.response.json").read_text())
    summary = response["choices"][0]["message"]["content"]
    context = json.loads((primary / f"{label}.context.json").read_text())["messages"]
    if context[-1]["content"] != "Recorded evidence:\n" + compose(summary, ""):
        raise ValueError("Baseline summary context does not match archived generation")
    return summary


def report(output, rows):
    """This diagnostic increases input size; it is not a matched-budget comparison."""
    table = aggregate(rows)
    write(output / "aggregate.json", table)
    lines = [
        "# Fixed-summary append diagnostic",
        "",
        "Post-hoc diagnostic motivated by the user's question; settings frozen before these additional calls.",
        "The baseline summary is unchanged byte-for-byte. Appended evidence increases input tokens.",
        (
            "Baselines reuse the primary run's two answers per compression generation; "
            "added contexts receive fresh answers."
        ),
        "",
        "| Case | Base allowance | Arm | Valid | Facts | All facts | Task checks all pass | Input tokens |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in table:
        prefix = (
            f"| {row['case']} | {row['budget']} | {row['arm']} | "
            f"{row['valid_compressions']}/{row['compressions']} |"
        )
        if row["valid_compressions"]:
            lines.append(
                prefix + f" {row['fact_accuracy']:.1%} | {row['all_facts']:.1%} | "
                f"{row['task_success']:.1%} | {row['prompt_tokens']:.0f} |",
            )
        else:
            lines.append(prefix + " — | — | — | — |")
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")


async def run(args):
    """Use archived scores and summary generations with fixed baseline summaries and archived decision scores."""
    from tokenizers import Tokenizer

    repo = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    primary = args.primary.resolve()
    if output.exists() or output == repo or repo in output.parents:
        raise ValueError("Use a new output directory outside the repository")
    values = dotenv_values(repo / ".env")
    if not values.get("LLM_API_KEY") or not values.get("LLM_BASE_URL"):
        raise ValueError("Missing authorized LLM configuration")
    protocol = json.loads((primary / "protocol.json").read_text())
    originals = json.loads((primary / "results.json").read_text())
    tokenizer = Tokenizer.from_file(str(args.tokenizer))

    def count(text):
        return len(tokenizer.encode(text).ids)

    bases = []
    for row in originals:
        if row["arm"] != "summary" or row["budget"] not in (600, 1000):
            continue
        if not row["valid"]:
            raise ValueError("A required baseline summary was invalid; do not regenerate it against scores")
        summary = frozen_base(primary, row["case"], row["compression_repeat"], row["budget"])
        bases.append({"row": row, "summary": summary, "sha256": hashlib.sha256(summary.encode()).hexdigest()})
    if len(bases) != 12:
        raise ValueError("Expected all twelve primary baseline generations to have completed")
    output.mkdir(parents=True)
    write(
        output / "protocol.json",
        {
            "primary": str(primary),
            "model": protocol["model"],
            "base_summary_allowances": [300, 600, 1000],
            "raw_caps": [200, 400],
            "controls": ["Jev200", "Jev400", "recency400"],
            "answer_repeats": 2,
            "concurrency": 4,
            "scope": "Post-hoc fixed-summary diagnostic, no matched total budget",
            "new_summaries": "Only six additional 300-token baselines; 600/1000 baselines reused",
            "no_new_decision_calls": True,
        },
    )
    for name in {base["row"]["case"] for base in bases}:
        (output / f"{name}.source.json").write_bytes((primary / f"{name}.source.json").read_bytes())
    for name in (
        "frozen_summary_experiment.py",
        "hybrid_experiment.py",
        "hybrid_cases.py",
        "run.py",
        "repair_check.py",
    ):
        (output / name).write_bytes((Path(__file__).parent / name).read_bytes())
    client = AsyncOpenAI(api_key=values["LLM_API_KEY"], base_url=values["LLM_BASE_URL"], timeout=90, max_retries=1)
    experiment = Experiment(client, output, protocol["model"], asyncio.Semaphore(4))
    semaphore = asyncio.Semaphore(4)
    rows = []

    async def append(base, selector, cap):
        async with semaphore:
            original = base["row"]
            name, repetition = original["case"], original["compression_repeat"]
            case = json.loads((primary / f"{name}.source.json").read_text())
            units = case["units"]
            scores = json.loads((primary / f"{name}.c{repetition}.scores.json").read_text())["scores"]
            order = (
                [u["id"] for u in reversed(units)]
                if selector == "recency"
                else [u["id"] for u in sorted(units, key=lambda u: (-scores[u["id"]], u["id"]))]
            )
            selected = pack(units, order, cap, count)
            payload = compose(base["summary"], render(selected))
            label = f"{name}.c{repetition}.base{original['budget']}.{selector}{cap}"
            trials = await experiment.evaluate(label, case, payload, 2)
            row = {
                "case": name,
                "arm": selector + str(cap),
                "budget": original["budget"],
                "valid": True,
                "compression_repeat": repetition,
                "summary_sha256": base["sha256"],
                "selected": [u["id"] for u in selected],
                "raw_cap": cap,
                "payload_tokens": count(payload),
                "compression_seconds": original["compression_seconds"],
                "trials": trials,
                "baseline_reused": False,
            }
            rows.append(row)
            write(output / "results.json", rows)
            report(output, rows)
            print(
                label,
                "facts",
                statistics.mean(sum(t["checks"]["facts"].values()) / len(t["checks"]["facts"]) for t in trials),
                flush=True,
            )

    async def new_baseline(name, repetition):
        case = json.loads((primary / f"{name}.source.json").read_text())
        scores = json.loads((primary / f"{name}.c{repetition}.scores.json").read_text())["scores"]
        label = f"{name}.c{repetition}.summary.300"
        payload, details = await experiment.context(
            label,
            case,
            case["units"],
            scores,
            "summary",
            300,
            count,
            tokenizer,
        )
        response = json.loads((output / f"{label}.summary.response.json").read_text())
        summary = response["choices"][0]["message"]["content"]
        trials = await experiment.evaluate(label, case, payload, 2)
        row = {
            "case": name,
            "family": case["family"],
            "compression_repeat": repetition,
            "arm": "summary",
            "budget": 300,
            "valid": True,
            "trials": trials,
            "payload_tokens": count(payload),
            "compression_seconds": details["summary_seconds"],
            **details,
        }
        bases.append({"row": row, "summary": summary, "sha256": hashlib.sha256(summary.encode()).hexdigest()})
        print(label, "baseline generated", flush=True)

    async def safe_baseline(name, repetition):
        try:
            await new_baseline(name, repetition)
        except Exception as exc:
            for arm in ("same_summary", "jev200", "jev400", "recency400"):
                rows.append(
                    {
                        "case": name,
                        "arm": arm,
                        "budget": 300,
                        "valid": False,
                        "trials": [],
                        "compression_repeat": repetition,
                        "error": f"Baseline unavailable: {exc}",
                    },
                )
            print(name, repetition, "INVALID baseline", str(exc), flush=True)

    async def safe_append(base, selector, cap):
        try:
            await append(base, selector, cap)
        except Exception as exc:
            rows.append(
                {
                    "case": base["row"]["case"],
                    "arm": selector + str(cap),
                    "budget": base["row"]["budget"],
                    "valid": False,
                    "trials": [],
                    "compression_repeat": base["row"]["compression_repeat"],
                    "error": str(exc),
                },
            )
            write(output / "results.json", rows)
            report(output, rows)

    try:
        async with asyncio.TaskGroup() as tasks:
            for name in sorted({b["row"]["case"] for b in bases}):
                for repetition in range(2):
                    tasks.create_task(safe_baseline(name, repetition))
        write(output / "frozen_bases.json", bases)
        for base in bases:
            row = base["row"]
            rows.append(
                {
                    **row,
                    "arm": "same_summary",
                    "summary_sha256": base["sha256"],
                    "baseline_reused": row["budget"] != 300,
                },
            )
        async with asyncio.TaskGroup() as tasks:
            for base in bases:
                for selector, cap in [("jev", 200), ("jev", 400), ("recency", 400)]:
                    tasks.create_task(safe_append(base, selector, cap))
        if any(values["LLM_API_KEY"].encode() in p.read_bytes() for p in output.rglob("*") if p.is_file()):
            raise RuntimeError("Credential in artifacts")
        report(output, rows)
        print("REPORT", output / "REPORT.md", flush=True)
    finally:
        await client.close()


def main():
    """Require explicit live execution and the completed primary run."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live; provider requests incur charges")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
