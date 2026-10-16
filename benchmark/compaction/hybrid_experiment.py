"""Frozen multi-budget comparison of summaries plus exact decision-selected evidence."""

import argparse
import asyncio
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import statistics
import time

from dotenv import dotenv_values
from openai import AsyncOpenAI

from benchmark.compaction.hybrid_cases import cases, evaluate, event_units, pack, render
from benchmark.compaction.run import SUMMARY, write
from benchmark.compaction.span_experiment import head_tail, score_units
from reme.components.as_decision_model import AgentScopeAsDecisionModel

ARMS = {
    "summary": 1.0,
    "spans": 0.0,
    "head_tail": 0.0,
    "hybrid70": 0.7,
    "hybrid50": 0.5,
    "hybrid30": 0.3,
    "rule_hybrid50": 0.5,
}


def compose(summary, raw):
    """Count both section labels and source citations inside the evidence budget."""
    return f"Summary:\n{summary}\n\nKey evidence:\n{raw}"


def allocations(budget, fraction, count):
    """Use fixed share caps; unused space is not transferred after seeing model answers."""
    available = budget - count(compose("", "")) - 8
    if available < 1:
        raise ValueError("Evidence budget is too small")
    summary = int(available * fraction)
    return summary, available - summary


def aggregate(rows):
    """Each table cell averages independent compressions and their repeated answers."""
    groups = {}
    for row in rows:
        key = (row["case"], row["budget"], row["arm"])
        groups.setdefault(key, []).append(row)
    result = []
    for (case, budget, arm), group in groups.items():
        valid = [r for r in group if r["valid"]]
        trials = [t for r in valid for t in r["trials"]]
        item = {
            "case": case,
            "budget": budget,
            "arm": arm,
            "valid_compressions": len(valid),
            "compressions": len(group),
        }
        if trials:
            item.update(
                {
                    "fact_accuracy": statistics.mean(
                        sum(t["checks"]["facts"].values()) / len(t["checks"]["facts"]) for t in trials
                    ),
                    "all_facts": statistics.mean(all(t["checks"]["facts"].values()) for t in trials),
                    "task_success": statistics.mean(all(t["checks"]["task"].values()) for t in trials),
                    "prompt_tokens": statistics.mean(t["usage"]["prompt_tokens"] for t in trials),
                    "payload_tokens": statistics.mean(r["payload_tokens"] for r in valid),
                    "compression_seconds": statistics.mean(r["compression_seconds"] for r in valid),
                },
            )
        result.append(item)
    return result


def report(output, rows):
    """Keep every arm and invalid compression visible rather than selecting winners."""
    table = aggregate(rows)
    write(output / "aggregate.json", table)
    lines = [
        "# Hybrid compaction experiment",
        "",
        "Two synthetic task families; the long payment case is a noise augmentation, not an independent task.",
        (
            "Two independent compressions and two answers per context. Scores "
            "below are descriptive, not significance tests."
        ),
        (
            "Task success means six executable payment tests or five structured "
            "replica-plan checks; these differ in scope."
        ),
        "",
        "| Case | Budget | Arm | Valid | Facts | All facts | Task checks all pass | Input tokens | Compaction s |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in table:
        prefix = (
            f"| {row['case']} | {row['budget'] or 'full'} | {row['arm']} | "
            f"{row['valid_compressions']}/{row['compressions']} |"
        )
        if row["valid_compressions"]:
            lines.append(
                prefix + f" {row['fact_accuracy']:.1%} | {row['all_facts']:.1%} | "
                f"{row['task_success']:.1%} | {row['prompt_tokens']:.0f} | {row['compression_seconds']:.2f} |",
            )
        else:
            lines.append(prefix + " — | — | — | — | — |")
    lines += [
        "",
        "Budget covers the entire summary/evidence payload, labels and citations; protected context is identical.",
        "Input usage is provider-reported; budgeting uses a local Qwen tokenizer proxy. No archive retrieval.",
        (
            "Jev scores are shared across budgets/ratios within a compression "
            "repetition. Each summary is generated separately."
        ),
        "The event-group splitter is new and shared by every arm; compare these arms with each other, not old runs.",
        "Hybrid summaries see the complete evidence and the selected snippets, with instructions to avoid duplication.",
        (
            "Generation failures, truncation and budget overruns are invalid, not "
            "repaired using answers. See results.json."
        ),
        "Costs are usage records by provider; token reduction alone does not establish total billing savings.",
    ]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass
class Experiment:
    """Own finite provider requests and durable experiment artifacts for one run."""

    client: AsyncOpenAI
    output: Path
    model: str
    semaphore: asyncio.Semaphore

    async def ask(self, label, context, *, summary=False):
        """Persist bodies without credentials; preserve failures as first-class records."""
        request = {
            "model": self.model,
            "messages": context,
            "temperature": 0,
            "max_tokens": 4096 if summary else 2400,
            "reasoning_effort": "none",
            "extra_body": {"enable_thinking": False},
        }
        if not summary:
            request["response_format"] = {"type": "json_object"}
        write(self.output / f"{label}.request.json", request)
        async with self.semaphore:
            started = time.monotonic()
            response = await self.client.chat.completions.create(**request)
            elapsed = time.monotonic() - started
        write(self.output / f"{label}.response.json", response.model_dump(mode="json"))
        record = {
            "seconds": elapsed,
            "usage": response.usage.model_dump() if response.usage else {},
            "model": response.model,
            "finish_reason": response.choices[0].finish_reason,
        }
        if record["finish_reason"] != "stop":
            raise ValueError(f"Incomplete {label}: {record['finish_reason']}")
        return response.choices[0].message.content, record

    async def context(self, label, case, units, scores, arm, budget, count, tokenizer):
        """Build one context without consulting exam questions or expected answers."""
        if arm == "full":
            return render(units), {
                "summary_tokens": 0,
                "raw_tokens": count(render(units)),
                "summary_usage": None,
                "summary_seconds": 0,
                "selected": [u["id"] for u in units],
            }
        if arm == "head_tail":
            return head_tail(render(units), budget, tokenizer), {
                "summary_tokens": 0,
                "summary_usage": None,
                "summary_seconds": 0,
                "selected": [],
            }
        fraction = ARMS[arm]
        summary_cap, raw_cap = allocations(budget, fraction, count)
        order = (
            [u["id"] for u in reversed(units)]
            if arm == "rule_hybrid50"
            else [u["id"] for u in sorted(units, key=lambda u: (-scores[u["id"]], u["id"]))]
        )
        selected = pack(units, order, raw_cap, count)
        raw = render(selected)
        summary, record = "", {"usage": None, "seconds": 0}
        if summary_cap:
            prompt = SUMMARY.format(words=max(20, int(summary_cap * 0.4))) + (
                f"\nThe summary must fit {summary_cap} Qwen tokens. "
                "Selected exact evidence will be appended separately. Cover useful "
                "information missing from those snippets. "
                "You may reference their IDs; avoid repeating their full text. "
                "Preserve important constraints and unresolved issues."
            )
            summary, record = await self.ask(
                label + ".summary",
                [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": case["messages"][1]["content"],
                                "history": units,
                                "selected_exact_evidence": selected,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                summary=True,
            )
            if count(summary) > summary_cap:
                raise ValueError(f"Summary over budget: {count(summary)} > {summary_cap}")
        payload = compose(summary, raw)
        if count(payload) > budget:
            raise ValueError(f"Combined payload over budget: {count(payload)} > {budget}")
        return payload, {
            "summary_tokens": count(summary),
            "raw_tokens": count(raw),
            "summary_cap": summary_cap,
            "raw_cap": raw_cap,
            "summary_usage": record["usage"],
            "summary_seconds": record["seconds"],
            "selected": [u["id"] for u in selected],
        }

    async def evaluate(self, label, case, payload, repeats):
        """Answer the frozen exam only after compaction has finished."""
        context = [*case["messages"][:2], {"role": "assistant", "content": "Recorded evidence:\n" + payload}]
        write(self.output / f"{label}.context.json", {"messages": context})
        trials = []
        for trial in range(repeats):
            text, record = await self.ask(
                f"{label}.trial{trial}",
                [*context, {"role": "user", "content": case["exam"]}],
            )
            answer = json.loads(text)
            trials.append({**record, "answer": answer, "checks": evaluate(case, answer)})
        return trials


async def run(args):
    """Freeze the complete matrix, then execute bounded concurrent experimental conditions."""
    from tokenizers import Tokenizer

    repo = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output.exists() or output == repo or repo in output.parents:
        raise ValueError("Use a new output directory outside the repository")
    values = dotenv_values(repo / ".env")
    secrets = [values.get(k) for k in ("LLM_API_KEY", "DECISION_MODEL_API_KEY")]
    if not all(secrets) or not values.get("LLM_BASE_URL"):
        raise ValueError("Missing authorized model configuration")
    source_bytes = args.trajectory.read_bytes()
    dataset = cases(args.trajectory)
    if not all(value in source_bytes.decode() for value in ("PAY-4827", "INV-731", "CH-991")):
        raise ValueError("The frozen payment exam requires the original pilot incident")
    if any(secret in json.dumps(dataset) for secret in secrets):
        raise ValueError("Credential in source")
    tokenizer = Tokenizer.from_file(str(args.tokenizer))

    def count(text):
        return len(tokenizer.encode(text).ids)

    output.mkdir(parents=True)
    write(
        output / "protocol.json",
        {
            "model": args.model,
            "budgets": args.budgets,
            "arms": ARMS,
            "compression_repeats": args.compressions,
            "answer_repeats": args.repeats,
            "concurrency": args.concurrency,
            "temperature": 0,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "tokenizer_sha256": hashlib.sha256(args.tokenizer.read_bytes()).hexdigest(),
            "summary_template": SUMMARY,
            "summary_word_cap": "max(20, floor(summary_cap * 0.4))",
            "allocation": "Reserve section labels + 8 tokens, then fixed share caps; no transfer of unused capacity",
            "splitter": (
                "Short files whole; group log lines by invoice/trace_id/request_id, " "routine lines in 600-char blocks"
            ),
            "rule_control": "Reverse source-unit order, greedily retain whole units under the same raw cap",
            "no_answer_tuning": True,
            "no_archive_retrieval": True,
            "scope": (
                "Two synthetic task families plus one controlled payment-noise "
                "variant; no statistical superiority claim"
            ),
            "budget_scope": (
                "Whole evidence payload, including headings/citations; actual prompt " "usage separately recorded"
            ),
        },
    )
    for name, case in dataset.items():
        write(output / f"{name}.source.json", {**case, "units": event_units(case["messages"])})
    for name in ("hybrid_experiment.py", "hybrid_cases.py", "span_experiment.py", "run.py", "repair_check.py"):
        (output / name).write_bytes((Path(__file__).parent / name).read_bytes())
    client = AsyncOpenAI(api_key=values["LLM_API_KEY"], base_url=values["LLM_BASE_URL"], timeout=90, max_retries=1)
    experiment = Experiment(client, output, args.model, asyncio.Semaphore(args.concurrency))
    credential = {
        "api_key": values["DECISION_MODEL_API_KEY"],
        "base_url": values.get("DECISION_MODEL_BASE_URL") or None,
    }
    model_name = values.get("DECISION_MODEL_NAME")
    model_name = None if model_name in (None, "", "null") else model_name
    rows = []
    condition_limit = asyncio.Semaphore(args.concurrency)

    async def condition(name, case, units, scores, decision_record, repetition, arm, budget):
        async with condition_limit:
            label = f"{name}.c{repetition}.{arm}.{budget or 'full'}"
            row = {
                "case": name,
                "family": case["family"],
                "compression_repeat": repetition,
                "arm": arm,
                "budget": budget,
                "valid": False,
                "trials": [],
            }
            try:
                payload, details = await experiment.context(label, case, units, scores, arm, budget, count, tokenizer)
                row.update(details)
                row["payload_tokens"] = count(payload)
                uses_decision = arm in {"spans", "hybrid70", "hybrid50", "hybrid30"}
                row["decision"] = decision_record if uses_decision else None
                row["compression_seconds"] = details["summary_seconds"] + (
                    decision_record["seconds"] if uses_decision else 0
                )
                row["trials"] = await experiment.evaluate(label, case, payload, args.repeats)
                row["valid"] = True
                accuracy = statistics.mean(
                    sum(t["checks"]["facts"].values()) / len(t["checks"]["facts"]) for t in row["trials"]
                )
                print(label, f"facts={accuracy:.0%}", "tokens=" + str(row["payload_tokens"]), flush=True)
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                print(label, "INVALID", row["error"], flush=True)
            rows.append(row)
            write(output / "results.json", rows)
            report(output, rows)

    try:
        async with AgentScopeAsDecisionModel(credential=credential, model=model_name, timeout=45) as decision:
            for name, case in dataset.items():
                units = event_units(case["messages"])
                for repetition in range(args.compressions):
                    visible = [{"id": u["id"], "file": u["file"], "text": u["text"]} for u in units]
                    scores, usage, seconds = await score_units(
                        decision,
                        visible,
                        case["messages"][1]["content"],
                        output,
                        f"{name}.c{repetition}",
                        goal=case["messages"][1]["content"],
                        next_action="Write the evidence-based investigation and next-action plan",
                    )
                    record = {"usage": usage, "seconds": seconds, "shared_across_conditions": True}
                    async with asyncio.TaskGroup() as tasks:
                        tasks.create_task(condition(name, case, units, scores, record, repetition, "full", None))
                        for budget in args.budgets:
                            for arm in ARMS:
                                tasks.create_task(condition(name, case, units, scores, record, repetition, arm, budget))
        if args.trajectory.read_bytes() != source_bytes:
            raise RuntimeError("Source trajectory changed")
        if any(secret.encode() in p.read_bytes() for p in output.rglob("*") if p.is_file() for secret in secrets):
            raise RuntimeError("Credential in artifacts")
        write(
            output / "validation.json",
            {
                "source_unchanged": True,
                "no_api_keys": True,
                "conditions": len(rows),
                "valid": sum(r["valid"] for r in rows),
            },
        )
        print("REPORT", output / "REPORT.md", flush=True)
    finally:
        await client.close()


def main():
    """Require live opt-in and explicit archived inputs; defaults freeze the primary matrix."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budgets", nargs="+", type=int, default=[600, 1000, 1600])
    parser.add_argument("--compressions", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--model", default="qwen3.8-max")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live or min([args.compressions, args.repeats, args.concurrency, *args.budgets]) < 1:
        parser.error("Use --live and positive budget/repetition/concurrency values; provider calls incur charges")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
