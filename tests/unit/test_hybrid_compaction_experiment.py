"""Offline contract checks for the frozen hybrid experiment."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path

from benchmark.compaction.hybrid_cases import REPLICA_GOLD, REPLICA_PLAN, evaluate, event_units, pack, render
from benchmark.compaction.hybrid_experiment import ARMS, Experiment, aggregate, allocations, compose


def test_event_groups_keep_correlated_lines_and_exact_offsets():
    """No expected labels are needed to preserve a shared event identity across routine logs."""
    text = "invoice=TEST-1 status=timeout\n" + "routine healthy\n" * 100 + "invoice=TEST-1 status=ok\n"
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "c", "function": {"arguments": '{"path":"log.txt"}'}},
            ],
        },
        {"role": "tool", "tool_call_id": "c", "content": json.dumps({"content": text})},
    ]
    before = deepcopy(messages)
    units = event_units(messages)
    linked = next(u for u in units if "status=timeout" in u["text"])
    assert "status=ok" in linked["text"] and len(linked["spans"]) == 2
    spans = sorted([s for u in units for s in u["spans"]], key=lambda s: s["start"])
    assert "".join(s["text"] for s in spans) == text
    assert all(text[s["start"] : s["end"]] == s["text"] for s in spans)
    assert messages == before
    selected = pack(units, [linked["id"]], len(render([linked])), len)
    assert selected == [linked]


def test_partition_counts_headers_and_preserves_share_caps():
    """A nominal budget includes headings, citations and an explicit token-boundary reserve."""
    for ratio in ARMS.values():
        summary, raw = allocations(600, ratio, len)
        assert summary >= 0 and raw >= 0
        assert summary + raw + len(compose("", "")) + 8 == 600
        assert len(compose("s" * summary, "r" * raw)) <= 600


def test_replica_grader_uses_exact_facts_and_all_procedure_constraints():
    """The new task has its own gold data and does not reuse payment repair checks."""
    case = {"family": "replica"}
    answer = {"facts": deepcopy(REPLICA_GOLD), "plan": deepcopy(REPLICA_PLAN)}
    checks = evaluate(case, answer)
    assert all(checks["facts"].values()) and all(checks["task"].values())
    answer["facts"]["slot_active"] = 0
    answer["plan"]["rollback"] = True
    answer["plan"]["success_condition"]["samples"] = 3.0
    checks = evaluate(case, answer)
    assert not checks["facts"]["slot_active"]
    assert not checks["task"]["rollback"] and not checks["task"]["success_condition"]


def test_hybrid_summary_never_receives_exam_or_gold():
    """The summary request sees the task, source units and retained snippets, not scoring material."""
    captured = []

    class FakeExperiment(Experiment):
        """Replace the network boundary, leaving real budgeting and composition intact."""

        async def ask(self, label, context, *, summary=False):
            """Capture a summary-only request without sending it."""
            assert label == "test.summary" and summary
            captured.append(context)
            return "Short summary.", {"usage": {}, "seconds": 1}

    case = {
        "messages": [{"role": "system", "content": "system"}, {"role": "user", "content": "task"}],
        "exam": "SECRET_EXAM",
        "gold": {"answer": "SECRET_GOLD"},
    }
    units = [{"id": "u1", "file": "x", "spans": [{"start": 0, "end": 7}], "text": "key=abc"}]
    experiment = FakeExperiment(None, Path("/tmp"), "fake", asyncio.Semaphore(1))
    payload, details = asyncio.run(experiment.context("test", case, units, {"u1": 0.9}, "hybrid50", 600, len, None))
    assert len(payload) <= 600 and details["selected"] == ["u1"]
    assert "key=abc" in payload
    assert "SECRET_EXAM" not in json.dumps(captured) and "SECRET_GOLD" not in json.dumps(captured)


def test_invalid_compression_stays_visible_in_aggregation():
    """Failed budget/output constraints cannot be counted as successful retained contexts."""
    result = aggregate([{"case": "case", "budget": 600, "arm": "summary", "valid": False, "trials": []}])
    assert result == [{"case": "case", "budget": 600, "arm": "summary", "valid_compressions": 0, "compressions": 1}]


def test_frozen_summary_preserves_exact_generation_and_rejects_rewrites(tmp_path):
    """Supplemental append comparisons cannot silently use a regenerated baseline summary."""
    import pytest

    from benchmark.compaction.frozen_summary_experiment import frozen_base
    from benchmark.compaction.run import write

    label = "payment_short.c0.summary.600"
    summary = "Keep this exact summary.\n"
    write(tmp_path / f"{label}.summary.response.json", {"choices": [{"message": {"content": summary}}]})
    context = [{"role": "assistant", "content": "Recorded evidence:\n" + compose(summary, "")}]
    write(tmp_path / f"{label}.context.json", {"messages": context})
    assert frozen_base(tmp_path, "payment_short", 0) == summary
    context[-1]["content"] = "Recorded evidence:\n" + compose(summary.strip(), "")
    write(tmp_path / f"{label}.context.json", {"messages": context})
    with pytest.raises(ValueError, match="does not match"):
        frozen_base(tmp_path, "payment_short", 0)


def test_content_diagnostic_does_not_accept_ambiguous_or_wrong_facts():
    """Secondary format normalization never replaces strict scoring or coerces booleans into counts."""
    from benchmark.compaction.analyze_hybrid import canonical
    from benchmark.compaction.run import exact_match

    assert canonical("retry.py line 5", 5, "key_generation_line") == 5
    assert canonical("retry.py:5", 5, "key_generation_line") == 5
    assert canonical("false", False) is False
    assert canonical("12900", 12900) == 12900
    assert not exact_match(canonical(True, 1), 1)
    assert not exact_match(canonical("line 5 or 7", 5, "key_generation_line"), 5)
    assert not exact_match(canonical("other.py line 5", 5, "key_generation_line"), 5)


def test_summary_aware_decision_observes_frozen_summary_without_exam():
    """Marginal usefulness is conditioned on the actual summary, without answer leakage."""
    from benchmark.compaction.summary_aware_experiment import observation

    case = {"messages": [{}, {"content": "task"}], "exam": "HIDDEN_EXAM", "gold": {"a": "HIDDEN_GOLD"}}
    base = {"summary": "Already covered: event X."}
    state, questions = observation(case, base, [{"id": "u1", "file": "log", "text": "event Y"}])
    assert state["frozen_summary"] == base["summary"]
    assert "HIDDEN_" not in json.dumps(state)
    assert "missing" in questions["u1"]["instructions"]
