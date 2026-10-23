"""Evaluate ReMe Image on the official MemLens memory-agent subset."""

import argparse
import base64
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
import io
import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import string

import yaml

# Adapted query/metric code retains its upstream MIT notice in README.md.
SYSTEM_PROMPT = (
    "Provide answers based on the given conversation history. "
    "If the question cannot be answered based on the given conversation, "
    'respond with "Insufficient information".'
)
INSTRUCTION = "Directly output the answer with no extra output."


def _image_path(root: Path, source: str) -> Path:
    """Resolve only original images inside the released image directory."""
    path = (root / source).resolve()
    if Path(source).is_absolute() or "\\" in source or not path.is_relative_to(root):
        raise ValueError("MemLens image must stay inside release_images")
    return path


def load_memlens(root: Path, context_length: str = "128k") -> list[dict]:
    """Select the official 195 IDs in dataset order, with each question's own history."""
    root = root.expanduser().resolve()
    source = root / f"dataset_{context_length}.json"
    selected = json.loads((root / "agent_subset_195.json").read_text(encoding="utf-8"))["question_ids"]
    if len(selected) != 195 or len(set(selected)) != 195:
        raise ValueError("MemLens requires its official 195-question agent subset")
    selected = set(selected)
    images = (root / "release_images").resolve()
    if not images.is_relative_to(root):
        raise ValueError("MemLens images must stay inside the dataset directory")
    result = []
    for row in json.loads(source.read_text(encoding="utf-8")):
        if row["question_id"] not in selected:
            continue
        sessions = []
        for turns, date, session_id in zip(
            row["haystack_sessions"],
            row["haystack_dates"],
            row["haystack_session_ids"],
            strict=True,
        ):
            for turn in turns:
                for image in turn.get("images", []):
                    _image_path(images, image["file"])
            sessions.append(
                {
                    "id": session_id,
                    "timestamp": datetime.strptime(date, "%Y/%m/%d (%a) %H:%M").isoformat(timespec="minutes"),
                    "turns": turns,
                    "question_id": row["question_id"],
                    "image_root": images,
                },
            )
        question = {
            "id": row["question_id"],
            "text": row["question"],
            "question_date": row["question_date"],
            "answer": row["answer"],
            "category": row["question_type"],
            "subtype": row.get("question_subtype", ""),
            "old_answer": row.get("old_answer") or row.get("question_content", {}).get("old_answer", ""),
        }
        result.append({"id": row["question_id"], "sessions": sessions, "questions": [question]})
    if len(result) != 195 or {scene["id"] for scene in result} != selected:
        raise ValueError("MemLens dataset must contain every selected question exactly once")
    return result


def image_block(path: Path) -> dict:
    """Encode untouched image bytes with their actual decoded MIME."""
    from PIL import Image

    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError(f"Oversized original image: {path.name}")
    data = path.read_bytes()
    if len(data) > 50 * 1024 * 1024:
        raise ValueError(f"Oversized original image: {path.name}")
    with Image.open(io.BytesIO(data)) as decoded:
        if decoded.width * decoded.height > 50_000_000:
            raise ValueError(f"Oversized original image dimensions: {path.name}")
        media_type = decoded.get_format_mimetype()
        if not media_type or not media_type.startswith("image/"):
            raise ValueError(f"Missing image MIME: {path.name}")
        decoded.load()
    return {
        "type": "data",
        "source": {
            "type": "base64",
            "data": base64.b64encode(data).decode("ascii"),
            "media_type": media_type,
        },
    }


def session_messages(session: dict) -> list[dict]:
    """Keep source roles, IDs, timestamps and the official <image> placement."""
    messages = []
    for index, turn in enumerate(session["turns"]):
        text, images = turn.get("content", ""), turn.get("images", [])
        if not images:
            stripped = text.replace("<image>", "").strip()
            parts = [stripped] if stripped else []
        elif "<image>" not in text:
            parts = [*images, *([text.strip()] if text.strip() else [])]
        else:
            parts, image_index = [], 0
            for part in re.split(r"(<image>)", text):
                if part == "<image>":
                    if image_index < len(images):
                        parts.append(images[image_index])
                        image_index += 1
                elif part.strip():
                    parts.append(part)
            parts.extend(images[image_index:])
        content = []
        for part in parts:
            if isinstance(part, str):
                content.append({"type": "text", "text": part})
            else:
                source = part["file"]
                content.extend(
                    [
                        {"type": "text", "text": f"[Image ID: {Path(source).stem}]"},
                        image_block(_image_path(session["image_root"], source)),
                    ],
                )
        messages.append(
            {
                "id": f"{session['question_id']}:{session['id']}:turn:{index}",
                "name": turn["role"],
                "role": turn["role"],
                "content": content,
                "created_at": session["timestamp"],
            },
        )
    return messages


def query_prompt(question: dict, context: str) -> str:
    """Keep the official dated query template unchanged."""
    return (
        f"{SYSTEM_PROMPT}\nConversation:\n{context}\n\n"
        f"{INSTRUCTION}\nQuestion Date: {question['question_date']}\nQuestion: {question['text']}\n"
    )


def parse_model_output(text: str) -> str:
    """Native special-token/think-trace parsing; retained raw outputs remain separate."""
    if not text:
        return ""
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    text = re.sub(r"<\|[^>]*\|>", "", text)
    text = re.sub(r"<\|begin_of_box\|>(.*?)<\|end_of_box\|>", r"\1", text, flags=re.DOTALL)
    text = text.replace("<|begin_of_box|>", "").replace("<|end_of_box|>", "")
    return text.replace("[CONTENT_FILTER_REJECTED]", "").strip()


def _normalize(text: str) -> str:
    """Native SubEM/F1 normalization, preserving decimal points and date slashes."""
    text = text.lower()
    text = "".join(
        (
            char
            if char not in string.punctuation
            or (char in "./" and 0 < index < len(text) - 1 and text[index - 1].isdigit() and text[index + 1].isdigit())
            else " "
        )
        for index, char in enumerate(text)
    )
    text = re.sub(r"\ba(?=\s+[a-z])", " ", text)
    text = re.sub(r"\b(an|the)\b", " ", text)
    return " ".join(text.split())


def score_answer(question: dict, prediction: str) -> dict:
    """Official inline auxiliary SubEM/F1; primary accuracy comes from the LLM judge."""
    predicted, expected = _normalize(parse_model_output(prediction)), _normalize(question["answer"])
    prediction_tokens, answer_tokens = predicted.split(), expected.split()
    overlap = sum((Counter(prediction_tokens) & Counter(answer_tokens)).values())
    return {
        "sub_em": float(bool(predicted and expected) and expected in predicted),
        "f1": 2 * overlap / (len(prediction_tokens) + len(answer_tokens)) if overlap else 0.0,
    }


_CURRENT = ContextVar("memlens_usage", default=None)
_KEYS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "noncached_input_tokens",
    "reasoning_tokens",
)


def normalized_usage(raw: dict) -> dict:
    """Keep unknown counters unknown; cache/reasoning are subsets, not extra tokens."""
    incoming = raw.get("input_tokens", raw.get("prompt_tokens"))
    outgoing = raw.get("output_tokens", raw.get("completion_tokens"))
    total = raw.get("total_tokens")
    if total is None and incoming is not None and outgoing is not None:
        total = incoming + outgoing
    cached = raw.get(
        "cached_input_tokens",
        raw.get("cached_tokens", (raw.get("prompt_tokens_details") or {}).get("cached_tokens")),
    )
    reasoning = raw.get("reasoning_tokens", (raw.get("completion_tokens_details") or {}).get("reasoning_tokens"))
    return {
        "input_tokens": incoming,
        "output_tokens": outgoing,
        "total_tokens": total,
        "cached_input_tokens": cached,
        "noncached_input_tokens": incoming - cached if incoming is not None and cached is not None else None,
        "reasoning_tokens": reasoning,
    }


def total_usage(records: list[dict]) -> dict:
    """Aggregate measured requests, recording coverage of optional counters."""
    return {
        key: (
            sum(row[key] for row in records if row.get(key) is not None)
            if any(row.get(key) is not None for row in records)
            else None
        )
        for key in _KEYS
    } | {
        "records": len(records),
        "coverage": {key: sum(row.get(key) is not None for row in records) for key in _KEYS},
    }


@contextmanager
def collect_usage():
    """Keep concurrent calls' usage separate and include their compression calls."""
    records = []
    token = _CURRENT.set(records)
    try:
        yield records
    finally:
        _CURRENT.reset(token)


def observe_usage(app) -> None:
    """Observe owned clients and distinguish native interrupted replies from answers."""
    for wrapper in app.context.components.get("agent_wrapper", {}).values():
        original_reply = wrapper.reply

        async def reply(*args, _reply=original_reply, **kwargs):
            result = await _reply(*args, **kwargs)
            last = result.get("last_message") or {}
            if last.get("finished_reason") == "interrupted" or last.get("error") is not None:
                raise RuntimeError("Native Agent was interrupted; see the application log.")
            return result

        wrapper.reply = reply
    for component in app.context.components.get("as_llm", {}).values():
        client = getattr(getattr(component.model, "client", None), "_client", None)
        if client is None or getattr(client, "_memlens_usage_observer", False):
            continue
        original = client.send

        async def send(request, *args, _send=original, **kwargs):
            response = await _send(request, *args, **kwargs)
            records = _CURRENT.get()
            if records is not None and response.status_code == 200 and response.is_stream_consumed:
                try:
                    payload = response.json()
                except (ValueError, UnicodeError):
                    payload = {}
                records.append(normalized_usage(payload.get("usage") or {}))
            return response

        client.send = send
        client._memlens_usage_observer = True  # pylint: disable=protected-access


def save(path: Path, value) -> None:
    """Save results, never model credentials or application secrets."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def app_config(workspace: Path, model: str, *, judge: bool = False) -> dict:
    """Resolve standard plugin settings through ReMe's configuration parser."""
    from reme.config import resolve_app_config

    values = resolve_app_config(
        config="benchmark" if judge else "memlens-benchmark",
        plugins=["memlens-judge" if judge else "memlens"],
        workspace_dir=str(workspace),
        log_config=False,
        enable_logo=False,
        log_to_console=False,
        log_to_file=True,
    )
    # BM25-only: do not start unused embedding clients.
    values["components"].pop("as_embedding", None)
    values["components"].pop("embedding_store", None)
    values["components"]["file_store"]["default"]["embedding_store"] = None
    if not judge:
        for name in ("default", "bench", "compressor"):
            values["components"]["as_llm"][name]["model"] = model
    else:
        values["jobs"] = {"answer_judge": {}}
        values["components"] = {}
    return values


def check_response(response):
    """Do not reinterpret execution failures as incorrect predictions."""
    if asyncio.current_task().cancelling():
        raise asyncio.CancelledError
    if not response.success:
        raise RuntimeError("ReMe Job failed; see this scene's application log.")
    return response


async def evaluate_scene(scene, number, model, group, judge, slots):
    """Accumulate one isolated history, then answer and judge its question."""
    from reme import Application

    label = re.sub(r"[^\w.-]+", "_", scene["id"])[:100]
    case = group / "reme_image" / "scenes" / f"{number:04d}-{label}"
    app = Application(**app_config(case / "ingestion/attempt-001/workspace", model))
    memory, answers, results = [], [], []
    memory_complete = False
    save(case / "source.json", {"id": scene["id"], "sessions": len(scene["sessions"])})
    try:
        await app.start()
        observe_usage(app)
        for ordinal, session in enumerate(scene["sessions"]):
            async with slots:
                with collect_usage() as requests:
                    response = check_response(
                        await app.run_job(
                            "auto_memory",
                            messages=await asyncio.to_thread(session_messages, session),
                            session_id=session["id"],
                            date=session["timestamp"][:10],
                            include_images=True,
                            include_source_sessions=True,
                        ),
                    )
            memory.extend(requests)
            save(
                case / "ingestion/attempt-001/sessions" / f"{ordinal:05d}.json",
                {
                    "session_id": session["id"],
                    "response": response.model_dump(),
                    "usage": total_usage(requests),
                },
            )
        check_response(await app.run_job("index_update"))
        memory_complete = True
        for index, question in enumerate(scene["questions"]):
            directory = case / "questions" / f"{index:04d}"
            query = question
            async with slots:
                with collect_usage() as requests:
                    response = check_response(
                        await app.run_job(
                            "agentic_answer",
                            query=query_prompt(query, "Use the available tools to retrieve relevant evidence."),
                            query_time=query["question_date"],
                            query_images=[],
                            scene_id=scene["id"],
                            include_images=True,
                            include_source_sessions=True,
                            max_iters=30,
                        ),
                    )
            answers.extend(requests)
            save(
                directory / "answer.json",
                {
                    "question_id": query["id"],
                    "prediction": response.answer,
                    "usage": total_usage(requests),
                    "agent": response.metadata,
                },
            )
            async with slots:
                judgment = check_response(
                    await judge.run_job(
                        "answer_judge",
                        question=query["text"],
                        reference=question["answer"],
                        prediction=response.answer,
                        category=query["category"],
                        subtype=question.get("subtype", ""),
                        old_answer=question.get("old_answer", ""),
                    ),
                )
            metrics = score_answer(question, response.answer)
            metrics["llm_judge"] = judgment.metadata["llm_judge_score"]
            save(directory / "judge.json", judgment.metadata)
            record = {
                "question_id": query["id"],
                "category": query["category"],
                "question": query["text"],
                "reference": question["answer"],
                "prediction": response.answer,
                "metrics": metrics,
            }
            save(directory / "result.json", record)
            results.append(record)
        save(case / "status.json", {"complete": True})
    except Exception as exc:  # pylint: disable=broad-exception-caught
        save(case / "status.json", {"complete": False, "error_type": type(exc).__name__})
    finally:
        await app.close()
    return results, memory if memory_complete else [], answers


async def run(settings: dict, model: str, length: str, limit: int | None = None) -> dict:
    """Run one model in a new output group; existing runs are never overwritten."""
    from reme import Application

    scenes = load_memlens(Path(settings["dataset"]), length)
    if limit is not None:
        scenes = scenes[:limit]
    group = Path(settings["output"]).expanduser().resolve() / f"memlens-{length}" / model
    group.mkdir(parents=True, exist_ok=False)
    effective = app_config(group / "unused-workspace", model)
    save(
        group / "settings.json",
        {
            "method": "reme_image",
            "model": model,
            "context_length": length,
            "dataset": str(Path(settings["dataset"]).expanduser().resolve()),
            "limit_scenes": limit,
            "include_source_sessions": True,
            "include_images": True,
            "answer_max_iters": 30,
            "config": settings,
            "models": {
                name: {key: value for key, value in spec.items() if key != "credential"}
                for name, spec in effective["components"]["as_llm"].items()
            },
            "reme_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        },
    )
    slots = asyncio.Semaphore(settings["query_concurrency"])
    scene_slots = asyncio.Semaphore(settings["scenario_concurrency"])
    judge = Application(**app_config(group / "judge-workspace", model, judge=True))
    try:
        await judge.start()

        async def evaluate(number, scene):
            async with scene_slots:
                print(f"Starting {length} {model} {scene['id']}", flush=True)
                result = await evaluate_scene(scene, number, model, group, judge, slots)
                print(f"Finished {scene['id']}: {len(result[0])}/{len(scene['questions'])} scored", flush=True)
                return result

        outputs = await asyncio.gather(*(evaluate(index, scene) for index, scene in enumerate(scenes)))
    finally:
        await judge.close()
    results = [row for output in outputs for row in output[0]]
    memory = [row for output in outputs for row in output[1]]
    answers = [row for output in outputs for row in output[2]]
    summary = {
        "method": "reme_image",
        "model": model,
        "context_length": length,
        "expected_questions": sum(len(scene["questions"]) for scene in scenes),
        "scored_questions": len(results),
        "metrics": {
            key: sum(row["metrics"][key] for row in results) / len(results) if results else None
            for key in ("llm_judge", "sub_em", "f1")
        },
        "memory_usage": total_usage(memory),
        "answer_usage": total_usage(answers),
        "token_usage": total_usage(memory + answers),
        "usage_policy": "successful memory/answer calls, including compression; judge excluded",
    }
    save(group / "summary.json", summary)
    return summary


def main():
    """Run one model at the requested MemLens history length."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--model", default="qwen3.8-max")
    parser.add_argument("--context-length", choices=("256k", "128k"), default="256k")
    parser.add_argument("--limit-scenes", type=int)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    settings = yaml.safe_load(os.path.expandvars(arguments.config.read_text(encoding="utf-8")))
    if arguments.output:
        settings["output"] = str(arguments.output)
    if arguments.limit_scenes is not None and arguments.limit_scenes < 1:
        parser.error("--limit-scenes must be positive")
    for key in ("query_concurrency", "scenario_concurrency"):
        if not isinstance(settings[key], int) or settings[key] < 1:
            parser.error(f"{key} must be positive")
    summary = asyncio.run(run(settings, arguments.model, arguments.context_length, arguments.limit_scenes))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["scored_questions"] == summary["expected_questions"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
