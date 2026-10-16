"""Frozen-summary incrementality, original evidence and deterministic payment scoring."""

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from benchmark.compaction.cases import GOLD, evaluate, event_units, exact_match, load_case, render, write
from benchmark.compaction.repair_check import repair_checks
from benchmark.compaction.run import Experiment, aggregate, answer, compose, decision_input, frozen_inputs, messages
from benchmark.compaction.run import prepare, top_n


class CharacterTokenizer:
    """Count characters so budget boundaries require no external tokenizer assets."""

    @staticmethod
    def encode(text, **_kwargs):
        """Match the tokenizer's small counting interface."""
        return SimpleNamespace(ids=list(text))


def experiment(tmp_path, cap=10000):
    """Use real packing with no live model clients."""
    return Experiment(None, None, tmp_path, CharacterTokenizer(), asyncio.Semaphore(1), "mock", cap)


def fixture():
    """Keep the oracle/exam separate from the task and evidence sent to compressors."""
    case = {
        "messages": [{"role": "system", "content": "system"}, {"role": "user", "content": "task"}],
        "exam": "PRIVATE_EXAM",
        "gold": {"value": "PRIVATE_GOLD"},
    }
    units = [
        {"id": str(i), "file": "file.txt", "text": f"source-{i}", "spans": [{"start": i, "end": i + 1}]}
        for i in range(3)
    ]
    return case, units


def test_top_n_is_strict_nested_score_prefix_with_source_order():
    """Retain even low-ranked evidence; do not threshold, skip or reorder it."""
    _, units = fixture()
    scores = {"0": 0.01, "1": 0.8, "2": 0.9}
    assert top_n(units, scores, 1) == units[2:]
    assert top_n(units, scores, 2) == units[1:]
    assert top_n(units, scores, 3) == units
    assert top_n(units, dict.fromkeys(scores, 0.1), 1) == units[:1]
    with pytest.raises(ValueError):
        top_n(units, scores, 4)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, -0.1, 1.1])
def test_invalid_rankings_never_become_top_n(value):
    """Malformed probabilities must not silently determine retained evidence."""
    _, units = fixture()
    with pytest.raises(ValueError):
        top_n(units, {"0": value, "1": 0.5, "2": 0.5}, 1)


def test_fusion_keeps_the_exact_same_summary_and_all_original_blocks(tmp_path):
    """Every N adds evidence while preserving S, protected prompts and evaluation question."""
    case, units = fixture()
    before = deepcopy((case, units))
    exp = experiment(tmp_path)
    rows = prepare(exp, case, units, ["Fixed summary."], [{"0": 0.1, "1": 0.8, "2": 0.9}], 3)
    baseline = json.loads((tmp_path / "c0.summary.context.json").read_text())["messages"]
    for row in rows[2:]:
        context = json.loads((tmp_path / f"c0.{row['arm']}.context.json").read_text())["messages"]
        assert row["summary"] == "Fixed summary."
        assert context[2]["content"].startswith(baseline[2]["content"])
        assert context[:2] == baseline[:2] and context[-1] == baseline[-1]
        chosen = [u for u in units if u["id"] in row["selected"]]
        assert context == messages(case, compose("Fixed summary.", render(chosen)))
    assert (case, units) == before


def test_over_budget_fusion_is_recorded_without_shrinking_s_or_skipping_raw(tmp_path):
    """Budget pressure cannot invalidate the incremental comparison by changing S."""
    case, units = fixture()
    exp = experiment(tmp_path, cap=1)
    rows = prepare(exp, case, units, ["Fixed S"], [{"0": 0.9, "1": 0.8, "2": 0.7}], 3)
    assert all(not row["within_budget"] for row in rows[1:])
    assert rows[-1]["selected"] == ["0", "1", "2"] and rows[-1]["summary"] == "Fixed S"
    asyncio.run(answer(exp, rows[-1], case, 1))
    assert not rows[-1]["valid"] and rows[-1]["trials"] == []


def test_actual_api_usage_overrun_invalidates_the_entire_condition(tmp_path):
    """A local estimate cannot substitute for checking actual downstream usage."""

    class FakeExperiment(Experiment):
        """Only mock the provider boundary."""

        async def ask(self, _label, _context, *, summary=False):
            """Return a complete answer whose provider reports too many input tokens."""
            return "{}", {"prompt_tokens": self.cap + 1}

    case, units = fixture()
    exp = FakeExperiment(None, None, tmp_path, CharacterTokenizer(), asyncio.Semaphore(1), "mock", 10000)
    row = prepare(exp, case, units, ["S"], [{"0": 0.1, "1": 0.2, "2": 0.3}], 1)[1]
    asyncio.run(answer(exp, row, case, 1))
    assert not row["valid"] and row["trials"] == []


def test_grouping_preserves_every_source_character_and_correlated_events():
    """Evidence grouping uses source correlations, never expected payment identifiers."""
    text = "".join(f"healthcheck {i}\n" for i in range(100))
    text += "event request_id=trace-a step=1\nevent request_id=trace-a step=2\n"
    history = [
        {"role": "assistant", "tool_calls": [{"id": "c", "function": {"arguments": '{"path":"log"}'}}]},
        {"role": "tool", "tool_call_id": "c", "content": json.dumps({"content": text})},
    ]
    units = event_units(history)
    spans = sorted([s for u in units for s in u["spans"]], key=lambda s: s["start"])
    assert "".join(s["text"] for s in spans) == text
    assert all(text[s["start"] : s["end"]] == s["text"] for s in spans)
    assert any("step=1" in u["text"] and "step=2" in u["text"] for u in units)


def test_compressors_see_task_and_source_but_no_exam_or_gold(tmp_path):
    """Usefulness scoring and summary generation cannot consult the follow-up oracle."""
    captured = []

    class FakeExperiment(Experiment):
        """Capture the real summary request without network calls."""

        async def ask(self, _label, context, *, summary=False):
            """Return a bounded summary."""
            captured.append(context)
            return "S", {"prompt_tokens": 10}

    case, units = fixture()
    state, _ = decision_input(case["messages"][1]["content"], units)
    exp = FakeExperiment(None, None, tmp_path, CharacterTokenizer(), asyncio.Semaphore(1), "mock", 10000)
    asyncio.run(exp.summarize("summary", "task", units, 100))
    assert "PRIVATE_" not in json.dumps([state, captured])
    supplied = json.loads(captured[0][1]["content"])
    assert supplied["remaining_evidence"] == units and supplied["retained_evidence"] == []


def test_frozen_replay_requires_every_generation_and_unchanged_evidence(tmp_path):
    """Do not select successful summaries or silently mix different trajectories."""
    case, units = fixture()
    write(tmp_path / "source.json", {**case, "units": units})
    write(tmp_path / "results.json", [{"arm": "summary", "repeat": 0, "summary": "S"}])
    (tmp_path / "provenance").mkdir()
    write(tmp_path / "provenance/paired.c0.decision0.response.json", {"scores": {"0": 0.2, "1": 0.8, "2": 0.9}})
    assert frozen_inputs(tmp_path, case, units, 1)[0] == ["S"]
    with pytest.raises(ValueError):
        frozen_inputs(tmp_path, case, units, 2)
    with pytest.raises(ValueError):
        frozen_inputs(tmp_path, {**case, "gold": {}}, units, 1)


def test_wrong_trajectory_cannot_be_scored_against_the_frozen_payment_oracle(tmp_path):
    """The known gold is specific to a pinned original source, not arbitrary input data."""
    path = tmp_path / "trajectory.json"
    path.write_text('{"messages": []}')
    with pytest.raises(ValueError, match="unchanged original"):
        load_case(path)


def test_grading_is_type_strict_and_failures_stay_in_denominator():
    """Boolean/integer equality and omitted failed conditions cannot inflate results."""
    assert not exact_match(True, 1) and not exact_match([True], [1])
    result = evaluate({"gold": GOLD}, {"facts": {**GOLD, "max_attempts": True}})
    assert sum(result["facts"].values()) == 9
    rows = [
        {"arm": "summary", "valid": False, "trials": []},
        {
            "arm": "summary",
            "valid": True,
            "trials": [
                {
                    "checks": {"facts": {"x": True}, "task": {"x": True}},
                    "usage": {"prompt_tokens": 100},
                },
            ],
        },
    ]
    assert aggregate(rows)[0]["facts"] == aggregate(rows)[0]["task"] == 0.5


def test_repair_behavior_checks_detect_unstable_keys_and_reject_unbounded_code():
    """Correct-looking plans do not substitute for six executable fake-client checks."""
    source = """def charge_with_retry(client, invoice, attempts=3):
    key = str(uuid.uuid4())
    for i in range(attempts):
        try:
            return client.charge(invoice, idempotency_key=key)
        except TimeoutError:
            if i == attempts - 1:
                raise
"""
    assert all(repair_checks(source).values())
    buggy = source.replace("    key = str(uuid.uuid4())\n", "").replace(
        "    for i in range(attempts):\n",
        "    for i in range(attempts):\n        key = str(uuid.uuid4())\n",
    )
    assert not repair_checks(buggy)["timeout_then_success"]
    assert not any(repair_checks("while True: pass").values())
