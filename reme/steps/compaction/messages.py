"""Pair and rebuild AgentScope blocks without rewriting conversation text."""

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
import json

from ...schema.compaction import CallDecision, CompactionRequest


@dataclass(frozen=True)
class ToolPair:
    """Block locations remain valid until all decisions have been collected."""

    id: str
    call_id: str
    tool: str
    input: dict
    call_location: tuple[int, int]
    result_location: tuple[int, int]
    result_chars: int
    protected: bool


def result_text(block: dict) -> str | None:
    """Only entirely textual outputs can be shortened."""
    output = block.get("output")
    if isinstance(output, str):
        return output
    if (
        isinstance(output, list)
        and output
        and all(
            isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
            for item in output
        )
    ):
        return "\n".join(item["text"] for item in output)
    return None


def collect_pairs(request: CompactionRequest) -> list[ToolPair]:
    """Ambiguous, incomplete, failed, unknown, or protected calls are never candidates."""
    calls, results = defaultdict(list), defaultdict(list)
    messages = request.messages
    recent = len(messages) - request.options.preserve_recent_messages
    protected = {
        index
        for index, message in enumerate(messages)
        if index == 0 or index >= recent or message.get("id") in request.protected_message_ids
    }
    for mi, message in enumerate(messages):
        for bi, block in enumerate(message["content"]):
            block_id = block.get("id")
            if not isinstance(block_id, str) or not block_id:
                continue
            if block.get("type") == "tool_call":
                calls[block_id].append((mi, bi))
            elif block.get("type") == "tool_result":
                results[block_id].append((mi, bi))
    pairs = []
    for call_id, locations in calls.items():
        if len(locations) != 1 or len(results[call_id]) != 1:
            continue
        ci, ri = locations[0], results[call_id][0]
        call, result = messages[ci[0]]["content"][ci[1]], messages[ri[0]]["content"][ri[1]]
        if ri <= ci:
            continue
        try:
            inputs = json.loads(call.get("input", ""))
            # Python accepts NaN/Infinity and overflowing numbers in JSON text.
            # Such inputs must stay untouched rather than break other candidates.
            json.dumps(inputs, allow_nan=False)
        except (TypeError, ValueError):
            continue
        if not isinstance(inputs, dict):
            continue
        text = result_text(result)
        pinned = (
            ci[0] in protected
            or ri[0] in protected
            or call_id in request.protected_call_ids
            or call.get("name") not in request.eligible_tool_names
            or call.get("state") != "finished"
            or result.get("state") != "success"
            or result.get("name") != call.get("name")
            or text is None
        )
        pairs.append(
            ToolPair(f"t{len(pairs) + 1}", call_id, call.get("name", ""), inputs, ci, ri, len(text or ""), pinned),
        )
    return pairs


def apply_decisions(
    messages: list[dict],
    pairs: list[ToolPair],
    decisions: list[CallDecision],
    head: int,
) -> list[dict]:
    """Work on a deep copy; delete only empty messages touched by a decision."""
    output = deepcopy(messages)
    by_id = {pair.id: pair for pair in pairs}
    removed: set[tuple[int, int]] = set()
    for decision in decisions:
        pair = by_id[decision.id]
        if pair.protected or decision.action == "keep":
            continue
        if decision.action == "drop_call":
            removed.update((pair.call_location, pair.result_location))
        else:
            mi, bi = pair.result_location
            block = output[mi]["content"][bi]
            text = result_text(block)
            marker = (
                f"\n[Compacted tool output; {len(text) - min(head, len(text))} chars omitted. "
                "Consult archived history.]"
            )
            shortened = text[:head] + marker
            if len(shortened) < len(text):
                block["output"] = shortened
    kept = []
    for mi, message in enumerate(output):
        content = [block for bi, block in enumerate(message["content"]) if (mi, bi) not in removed]
        if content or len(content) == len(message["content"]):
            message["content"] = content
            kept.append(message)
    return kept
