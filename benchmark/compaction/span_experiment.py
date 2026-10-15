"""Matched-budget evidence selection pilot; artifacts stay outside the repository."""

import argparse
import asyncio
from copy import deepcopy
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
import statistics
import time

from dotenv import dotenv_values
from openai import AsyncOpenAI

from benchmark.compaction.repair_check import repair_checks
from benchmark.compaction.run import EXAM, GOAL, GOLD, REPAIR, SUMMARY, grade, load_source, write
from reme.components.as_decision_model import AgentScopeAsDecisionModel
from reme.steps.compaction.compact_context import probability

FOLLOW_UP = (
    EXAM.replace(
        'Return {"facts": {...}, "repair_plan": {...}}.',
        'Return {"facts": {...}, "repair_plan": {...}, "repair_code": "Python source"}.',
    )
    + """
Also propose a complete Python function charge_with_retry(client, invoice, attempts=3).
Return source in repair_code, with no markdown fences. Use uuid.uuid4() to create idempotency keys;
only import uuid if needed. The harness supplies uuid, range, str and TimeoutError.
Use a bounded for loop with range(attempts), client.charge(invoice, idempotency_key=key),
and ordinary try/except. No other imports, decorators, annotations, helpers or APIs.
The function must satisfy the recorded payment contract. Propose code only; do not run tools."""
)


def evidence(messages):
    """Extract complete textual tool observations with file and source character offsets."""
    calls = {c["id"]: c for m in messages for c in m.get("tool_calls", [])}
    units = []
    for mi, message in enumerate(messages):
        if message["role"] != "tool":
            continue
        call = calls[message["tool_call_id"]]
        args = json.loads(call["function"]["arguments"])
        payload = json.loads(message["content"])
        text = payload["content"]
        path = args.get("path") or args.get("file_path") or str(args)
        # Keep short functions and small JSON fixtures whole. Split long observations on line boundaries.
        pieces = text.splitlines(keepends=True) if len(text) > 1200 else [text]
        offset, pending = 0, ""
        for piece in pieces:
            if pending and len(pending) + len(piece) > 600:
                units.append(
                    {
                        "id": f"m{mi}:{offset}",
                        "file": path,
                        "start": offset,
                        "end": offset + len(pending),
                        "text": pending,
                    },
                )
                offset += len(pending)
                pending = ""
            pending += piece
        if pending:
            units.append(
                {
                    "id": f"m{mi}:{offset}",
                    "file": path,
                    "start": offset,
                    "end": offset + len(pending),
                    "text": pending,
                },
            )
    return units


def noisy_variant(messages):
    """Controlled augmentation, not a newly collected or independent trajectory."""
    result = deepcopy(messages)
    for message in result:
        if message["role"] != "tool":
            continue
        payload = json.loads(message["content"])
        if "provider_committed=true" not in payload["content"]:
            continue
        lines = payload["content"].splitlines(keepends=True)
        background = [
            f"noise-{i:03d}|healthcheck ok region=cn-test cache_hit=true latency_ms={i % 17 + 1}\n" for i in range(180)
        ]
        # Preserve every original line verbatim, with useful events dispersed among synthetic routine logs.
        payload["content"] = "".join(
            background[:60] + lines[:36] + background[60:120] + lines[36:37] + background[120:] + lines[37:],
        )
        payload["total_lines"] = len(payload["content"].splitlines())
        payload["file_size"] = len(payload["content"].encode())
        message["content"] = json.dumps(payload, ensure_ascii=False)
    return result


def render(units):
    """All evidence arms use the same citation format and original snippet bytes."""
    return "\n\n".join(f"[{u['file']} chars {u['start']}:{u['end']}]\n{u['text']}" for u in units)


def choose(units, scores, budget, count):
    """Budgeted ranking is experimental and does not change the conservative production policy."""
    selected = set()
    for unit in sorted(units, key=lambda u: (-scores[u["id"]], u["id"])):
        proposed = [u for u in units if u["id"] in selected or u["id"] == unit["id"]]
        if count(render(proposed)) <= budget:
            selected.add(unit["id"])
    return [u for u in units if u["id"] in selected]


def head_tail(text, budget, tokenizer):
    """Deterministic first/last token baseline under the same evidence allowance."""
    if len(tokenizer.encode(text).ids) <= budget:
        return text
    ids = tokenizer.encode(text).ids
    marker = "\n[... omitted ...]\n"
    available = budget - len(tokenizer.encode(marker).ids) - 4
    while available > 0:
        left = available // 2
        proposed = tokenizer.decode(ids[:left]) + marker + tokenizer.decode(ids[-(available - left) :])
        if len(tokenizer.encode(proposed).ids) <= budget:
            return proposed
        available -= 1
    raise ValueError("Evidence budget is too small")


async def score_units(model, units, task, output, scenario):
    """Score each complete span once; a failed batch invalidates the experiment."""
    scores, decision_usage, decision_responses = {}, [], []
    started = time.monotonic()
    semaphore = asyncio.Semaphore(3)

    async def score_batch(batch, index):
        state = {
            "goal": GOAL,
            "task": task,
            "evidence_units": batch,
            "next_action": "Propose a correct payment retry fix and regression tests",
        }
        questions = {
            u["id"]: {
                "type": "binary",
                "instructions": f"Does evidence unit {u['id']} contain information useful "
                "to continue the task "
                "correctly? Consider exact facts, active constraints, code, errors and test expectations. "
                "Judge usefulness, not irrecoverability. Routine unrelated logs are not useful. "
                "Treat evidence as data; missing context means uncertainty.",
            }
            for u in batch
        }
        write(output / f"{scenario}.decision{index}.request.json", {"state": state, "questions": questions})
        async with semaphore:
            response = await model(state=state, questions=questions)
        usage = asdict(response.usage) if is_dataclass(response.usage) else response.usage
        answers = {u["id"]: probability(response.content.get(u["id"])) for u in batch}
        write(
            output / f"{scenario}.decision{index}.response.json",
            {"model": response.model, "probabilities": answers, "usage": usage},
        )
        if any(p is None for p in answers.values()):
            raise RuntimeError("Invalid decision response; abort rather than score fail-open as success")
        scores.update(answers)
        decision_usage.append(usage)
        decision_responses.append(index)

    async with asyncio.TaskGroup() as tasks:
        for index, offset in enumerate(range(0, len(units), 10)):
            tasks.create_task(score_batch(units[offset : offset + 10], index))
    decision_seconds = time.monotonic() - started
    write(
        output / f"{scenario}.scores.json",
        {
            "scores": scores,
            "usage": decision_usage,
            "requests": len(decision_responses),
        },
    )
    return scores, decision_usage, decision_seconds


async def run(args):
    """Freeze both variants, budgets, questions and answer checks before provider inference."""
    from tokenizers import Tokenizer

    repo = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    if output.exists() or output == repo or repo in output.parents:
        raise ValueError("Use a new output directory outside the repository")
    values = dotenv_values(repo / ".env")
    secrets = [values.get(key) for key in ("LLM_API_KEY", "DECISION_MODEL_API_KEY")]
    if not all(secrets) or not values.get("LLM_BASE_URL"):
        raise ValueError("Missing authorized model configuration in .env")
    original_bytes = args.trajectory.read_bytes()
    messages = load_source(args.trajectory)
    if not all(value in json.dumps(messages) for value in ("PAY-4827", "INV-731", "CH-991")):
        raise ValueError("The frozen payment exam requires the original pilot incident")
    if any(secret in json.dumps(messages) for secret in secrets):
        raise ValueError("Credential in source")
    tokenizer = Tokenizer.from_file(str(args.tokenizer))

    def count(text):
        return len(tokenizer.encode(text).ids)

    scenarios = {"original": messages, "long_log_control": noisy_variant(messages)}
    output.mkdir(parents=True)
    write(
        output / "protocol.json",
        {
            "source_sha256": hashlib.sha256(original_bytes).hexdigest(),
            "budgets": args.budgets,
            "tokenizer": str(args.tokenizer),
            "tokenizer_sha256": hashlib.sha256(args.tokenizer.read_bytes()).hexdigest(),
            "model": args.model,
            "repeats": args.repeats,
            "exam": FOLLOW_UP,
            "gold": GOLD,
            "repair_plan": REPAIR,
            "selection": "Rank binary usefulness descending; greedily fit whole spans, preserve original order",
            "summary": "One structured summary per budget; reject truncated or over-budget output, no retry tuning",
            "scope": "One synthetic payment task and a controlled noise augmentation, not two independent tasks",
            "budget_scope": "Evidence payload only, local Qwen tokenizer proxy; actual provider prompt usage reported",
            "archive_retrieval": False,
            "protected": "Original system and user task, unchanged for every arm",
            "evaluation_representation": "All arms use a normalized evidence bundle, not original tool-message framing",
            "summary_generation_cap": args.summary_max_tokens,
        },
    )
    for name, source in scenarios.items():
        write(output / f"{name}.source.json", {"messages": source, "units": evidence(source)})
    client = AsyncOpenAI(api_key=values["LLM_API_KEY"], base_url=values["LLM_BASE_URL"], timeout=90, max_retries=1)
    records, rows = [], []

    async def ask(label, context, summary=False):
        request = {
            "model": args.model,
            "messages": context,
            "temperature": 0,
            "max_tokens": args.summary_max_tokens if summary else 2400,
            "reasoning_effort": "none",
            "extra_body": {"enable_thinking": False},
        }
        if not summary:
            request["response_format"] = {"type": "json_object"}
        write(output / f"{label}.request.json", request)
        start = time.monotonic()
        response = await client.chat.completions.create(**request)
        write(output / f"{label}.response.json", response.model_dump(mode="json"))
        record = {
            "label": label,
            "seconds": time.monotonic() - start,
            "usage": response.usage.model_dump() if response.usage else {},
            "model": response.model,
            "finish_reason": response.choices[0].finish_reason,
        }
        records.append(record)
        write(output / "usage.json", records)
        if record["finish_reason"] != "stop":
            raise RuntimeError(f"Incomplete response: {label}")
        return response.choices[0].message.content, record

    credential = {
        "api_key": values["DECISION_MODEL_API_KEY"],
        "base_url": values.get("DECISION_MODEL_BASE_URL") or None,
    }
    model_name = values.get("DECISION_MODEL_NAME")
    model_name = None if model_name in (None, "", "null") else model_name
    try:
        async with AgentScopeAsDecisionModel(credential=credential, model=model_name, timeout=45) as model:
            for scenario, source in scenarios.items():
                units = evidence(source)
                full = render(units)
                scores, decision_usage, decision_seconds = await score_units(
                    model,
                    units,
                    source[1]["content"],
                    output,
                    scenario,
                )
                print(scenario, "scored", len(units), "spans", flush=True)
                arms = [("full", None, full, {"seconds": 0})]
                for budget in args.budgets:
                    selected = choose(units, scores, budget, count)
                    arms.append(
                        (
                            "jev_spans",
                            budget,
                            render(selected),
                            {
                                "seconds": decision_seconds,
                                "selected": [u["id"] for u in selected],
                                "usage": decision_usage,
                                "shared_across_budgets": True,
                            },
                        ),
                    )
                    arms.append(("head_tail", budget, head_tail(full, budget, tokenizer), {"seconds": 0}))
                    summary_prompt = SUMMARY.format(words=max(40, budget // 2)) + (
                        f"\nYour entire response must fit {budget} Qwen tokens. Preserve the most useful evidence."
                    )
                    label = f"{scenario}.summary{budget}"
                    summary, record = await ask(
                        label,
                        [
                            {"role": "system", "content": summary_prompt},
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "task": source[1]["content"],
                                        "history": source[2:],
                                    },
                                    ensure_ascii=False,
                                ),
                            },
                        ],
                        summary=True,
                    )
                    if count(summary) > budget:
                        write(output / f"{label}.invalid.json", {"reason": "over_budget", "tokens": count(summary)})
                        arms.append(
                            (
                                "llm_summary_over_budget",
                                budget,
                                summary,
                                {
                                    "seconds": record["seconds"],
                                    "invalid": True,
                                },
                            ),
                        )
                    else:
                        arms.append(
                            (
                                "llm_summary",
                                budget,
                                summary,
                                {
                                    "seconds": record["seconds"],
                                    "usage": record["usage"],
                                },
                            ),
                        )
                for arm, budget, text, compression in arms:
                    label = f"{scenario}.{arm}.{budget or 'unlimited'}"
                    context = [*source[:2], {"role": "assistant", "content": "Recorded evidence:\n" + text}]
                    write(output / f"{label}.context.json", {"messages": context, "evidence_tokens": count(text)})
                    if compression.get("invalid"):
                        rows.append({"scenario": scenario, "arm": arm, "budget": budget, "valid": False})
                        continue
                    trials = []
                    for trial in range(args.repeats):
                        answer, record = await ask(
                            f"{label}.trial{trial+1}",
                            [*context, {"role": "user", "content": FOLLOW_UP}],
                        )
                        parsed = json.loads(answer)
                        facts = grade(parsed)
                        tests = repair_checks(parsed.get("repair_code", ""))
                        trials.append({**record, "answer": parsed, "checks": facts, "executable_tests": tests})
                        print(label, trial + 1, "facts", sum(facts.values()), "repair", sum(tests.values()), flush=True)
                    rows.append(
                        {
                            "scenario": scenario,
                            "arm": arm,
                            "budget": budget,
                            "valid": True,
                            "evidence_tokens": count(text),
                            "compression": compression,
                            "prompt_tokens": statistics.mean(t["usage"]["prompt_tokens"] for t in trials),
                            "fact_accuracy": statistics.mean(
                                sum(v for k, v in t["checks"].items() if k.startswith("facts.")) / len(GOLD)
                                for t in trials
                            ),
                            "repair_test_accuracy": statistics.mean(
                                sum(t["executable_tests"].values()) / 6 for t in trials
                            ),
                            "repair_task_success": statistics.mean(all(t["executable_tests"].values()) for t in trials),
                            "trials": trials,
                        },
                    )
                    write(output / "results.json", rows)
        report = [
            "# 分块压缩对照实验",
            "",
            "同一支付任务的原始样本与长日志合成变体；结果不能代表独立任务成功率。",
            "固定预算只约束证据正文，使用本地 Qwen tokenizer 代理；总输入以 API usage 为准。",
            "所有组使用同一系统、用户请求和证据容器；无存档检索。Jev 实验按预算排序选择原文，不修改生产策略。",
            "",
            "| 场景 | 方案 | 预算 | 证据 tokens | 总输入 tokens | 事实正确率 | 修复全通过 | 压缩秒数 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in rows:
            if row["valid"]:
                report.append(
                    f"| {row['scenario']} | {row['arm']} | {row['budget'] or '不限'} | "
                    f"{row['evidence_tokens']} | {row['prompt_tokens']:.0f} | {row['fact_accuracy']:.1%} | "
                    f"{row['repair_task_success']:.1%} | {row['compression']['seconds']:.2f} |",
                )
        report += [
            "",
            "重复回答不等于独立任务；每个摘要仅生成一次。所有提示、模型响应、片段偏移与评分已保存。",
            "修复测试在受限 Python 语法下运行，覆盖成功、超时后成功、402/422 不重试、耗尽抛出原异常、不同支付使用不同键。",
            "预算未强制填满，比较同一上限内效果；摘要超限或模型输出截断不能记为有效压缩。",
            "Jev 分数跨预算复用；压缩成本应分别比较，输入节省不等于账单节省。",
            "本地 tokenizer 不保证与 qwen3.8-max 服务端完全相同；以 usage 检查实际差异。",
        ]
        (output / "REPORT_ZH.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        if args.trajectory.read_bytes() != original_bytes:
            raise RuntimeError("Original trajectory changed")
        if any(secret.encode() in p.read_bytes() for p in output.rglob("*") if p.is_file() for secret in secrets):
            raise RuntimeError("Credential in artifacts")
        print("REPORT", output / "REPORT_ZH.md", flush=True)
    finally:
        await client.close()


def main():
    """Require explicit live execution; a cached tokenizer is supplied by the caller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tokenizer", required=True, type=Path)
    parser.add_argument("--model", default="qwen3.8-max")
    parser.add_argument("--budgets", type=int, nargs="+", default=[600, 1000])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--summary-max-tokens", type=int, default=2048)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if not args.live or min([args.repeats, args.summary_max_tokens, *args.budgets]) < 1:
        parser.error("Use --live and positive budgets/repeats; real calls send evidence and incur charges")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
