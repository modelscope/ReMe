"""Check experimental selection fidelity and the executable payment grader without providers."""

import pytest

from benchmark.compaction.repair_check import repair_checks
from benchmark.compaction.cases import event_units, render
from benchmark.compaction.run import select

FIX = """
import uuid

def charge_with_retry(client, invoice, attempts=3):
    key = str(uuid.uuid4())
    for attempt in range(attempts):
        try:
            return client.charge(invoice, idempotency_key=key)
        except TimeoutError:
            if attempt == attempts - 1:
                raise
"""


def test_repair_grader_rejects_original_bug():
    """Passing the grammar alone cannot pass the semantic test cases."""
    assert all(repair_checks(FIX).values())
    broken = FIX.replace("    key = str(uuid.uuid4())\n", "").replace(
        "    for attempt in range(attempts):\n",
        "    for attempt in range(attempts):\n        key = str(uuid.uuid4())\n",
    )
    checks = repair_checks(broken)
    assert not checks["timeout_then_success"]
    assert not checks["exhaustion"]
    assert checks["http_422"]


@pytest.mark.parametrize(
    "code",
    [
        "import os\n" + FIX,
        FIX.replace("range(attempts)", "range(1000)"),
        FIX.replace("return client.charge", "return open"),
        FIX.replace("    key =", "    while True: pass\n    key ="),
    ],
)
def test_repair_grader_rejects_unbounded_or_external_programs(code):
    """Generated code has no access to host files, tools or unbounded iteration."""
    assert not any(repair_checks(code).values())


def test_ranked_selection_preserves_source_order_and_final_budget():
    """Selection must account for wrapper/protected text, not only evidence length."""
    units = [{"id": str(i), "file": "x", "spans": [{"start": i, "end": i + 1}], "text": "abc"} for i in range(3)]
    limit = len(render([units[0], units[2]]))
    before = repr(units)
    selected = select(units, {"0": 0.8, "1": 0.1, "2": 0.9}, lambda raw: len(raw) <= limit)
    assert selected == [units[0], units[2]]
    assert repr(units) == before
    assert select(units, dict.fromkeys(["0", "1", "2"], 0.5), lambda raw: len(raw) <= 1) == []


def test_event_groups_reconstruct_source_and_link_noncontiguous_events():
    """The splitter retains every original character and shared event identity."""
    import json

    text = "invoice=INV-X timeout=true\n" + "routine line\n" * 130 + "invoice=INV-X committed=true\n"
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "a", "function": {"arguments": '{"path":"incident.log"}'}},
            ],
        },
        {"role": "tool", "tool_call_id": "a", "content": json.dumps({"content": text})},
    ]
    before = json.dumps(messages)
    units = event_units(messages)
    spans = sorted([span for u in units for span in u["spans"]], key=lambda s: s["start"])
    assert "".join(s["text"] for s in spans) == text
    assert all(text[s["start"] : s["end"]] == s["text"] for s in spans)
    linked = next(u for u in units if "timeout=true" in u["text"])
    assert "committed=true" in linked["text"] and len(linked["spans"]) == 2
    assert json.dumps(messages) == before


def test_fact_grading_rejects_wrong_nested_types():
    """Nested booleans/floats must not receive credit for integer counts or keys."""
    from copy import deepcopy

    from benchmark.compaction.cases import GOLD, REPAIR, grade

    answer = {"facts": deepcopy(GOLD), "repair_plan": deepcopy(REPAIR)}
    assert all(grade(answer).values())
    answer["facts"]["regression_attempt_counts"]["validation_422"] = True
    answer["facts"]["no_retry_http_statuses"] = [402.0, 422.0]
    checks = grade(answer)
    assert not checks["facts.regression_attempt_counts"]
    assert not checks["facts.no_retry_http_statuses"]
    assert not any(grade([]).values())


def test_complete_input_budget_includes_protected_context_and_exam(tmp_path):
    """A large protected prompt consumes the same allowance in every compressed arm."""
    import asyncio
    from types import SimpleNamespace

    from benchmark.compaction.run import Experiment, compose, messages

    class Tokenizer:
        """Count characters to make the complete-message boundary deterministic."""

        @staticmethod
        def encode(text, **_kwargs):
            """Return a minimal tokenizer-like result."""
            return SimpleNamespace(ids=list(text))

    case = {
        "messages": [{"role": "system", "content": "S" * 100}, {"role": "user", "content": "task"}],
        "exam": "E" * 100,
    }
    exp = Experiment(None, None, tmp_path, Tokenizer(), asyncio.Semaphore(1), "mock", 10000)
    payload = compose("summary", "evidence")
    exp.cap = exp.input_tokens(messages(case, payload)) + 64
    assert exp.fits(case, payload)
    assert not exp.fits(case, payload + "x")
    assert messages(case) == [*case["messages"], {"role": "user", "content": case["exam"]}]


def test_decision_inputs_exclude_exam_and_gold():
    """Both selection methods receive only the current task and original evidence."""
    import json

    from benchmark.compaction.run import decision_input

    state, questions = decision_input("task", [{"id": "u", "file": "log", "text": "event"}])
    assert set(state) == {"task", "evidence_units"}
    assert "continue the task" in questions["u"]["instructions"]
    assert "exam" not in json.dumps(state) and "gold" not in json.dumps(state)


def test_failed_conditions_score_zero_instead_of_being_dropped():
    """Aggregate denominators include all planned conditions, including budget failures."""
    from benchmark.compaction.run import aggregate

    rows = [
        {"case": "x", "arm": "summary", "valid": False, "trials": []},
        {
            "case": "x",
            "arm": "summary",
            "valid": True,
            "trials": [
                {"checks": {"facts": {"a": True}, "task": {"b": True}}, "usage": {"prompt_tokens": 100}},
            ],
        },
    ]
    row = next(r for r in aggregate(rows) if r["arm"] == "summary")
    assert row["valid"] == 1 and row["attempted"] == 2
    assert row["facts"] == row["task"] == 0.5


def test_variant_grader_uses_its_own_identifiers():
    """Fresh variant answers are checked against their own frozen source, not the pilot identifiers."""
    from copy import deepcopy

    from benchmark.compaction.cases import REPLICA_GOLD, REPLICA_PLAN, evaluate

    case = {
        "family": "replica",
        "gold": {**REPLICA_GOLD, "incident_id": "INC-FRESH"},
        "plan_gold": REPLICA_PLAN,
    }
    answer = {"facts": deepcopy(case["gold"]), "plan": deepcopy(REPLICA_PLAN)}
    assert all(evaluate(case, answer)["facts"].values())
    answer["facts"]["incident_id"] = REPLICA_GOLD["incident_id"]
    assert not evaluate(case, answer)["facts"]["incident_id"]


def test_fusion_summarizes_remaining_evidence_without_exam_or_gold(tmp_path):
    """Raw selection and summary share one complete-message ceiling; the summarizer sees both partitions."""
    import asyncio
    import json
    from types import SimpleNamespace

    from benchmark.compaction.run import Experiment

    captured = []

    class Tokenizer:
        """Count characters deterministically."""

        @staticmethod
        def encode(text, **_kwargs):
            """Expose a tokenizer-compatible count."""
            return SimpleNamespace(ids=list(text))

    class FakeExperiment(Experiment):
        """Mock only provider requests while exercising real selection, composition and grading."""

        async def scores(self, _label, _task, _units):
            """Select one exact group, leave the other for summarization."""
            return {"u1": 0.9, "u2": 0.1}, []

        async def ask(self, _label, context, *, summary=False):
            """Capture summary inputs; return a valid deterministic replica response for evaluation."""
            captured.append((summary, context))
            return ("Complementary summary." if summary else '{"facts": {}, "plan": {}}'), {"prompt_tokens": 900}

    case = {
        "messages": [{"role": "system", "content": "system"}, {"role": "user", "content": "task"}],
        "exam": "HIDDEN_EXAM",
        "gold": {"event": "HIDDEN_GOLD"},
        "plan_gold": {},
        "family": "replica",
    }
    units = [
        {"id": f"u{i}", "file": "log", "text": f"event-{i}", "spans": [{"start": i, "end": i + 1}]} for i in (1, 2)
    ]
    row = {"case": "case", "repeat": 0, "arm": "fusion"}
    exp = FakeExperiment(None, None, tmp_path, Tokenizer(), asyncio.Semaphore(1), "mock", 1000)
    asyncio.run(exp.condition(row, case, units, 1))
    assert row["valid"] and row["selected"] == ["u1"]
    summary_requests = [context for summary, context in captured if summary]
    assert len(summary_requests) == 1
    supplied = json.loads(summary_requests[0][1]["content"])
    assert supplied["retained_evidence"] == units[:1]
    assert supplied["remaining_evidence"] == units[1:]
    assert "HIDDEN_" not in json.dumps(summary_requests)
    context = json.loads((tmp_path / "case.c0.fusion.context.json").read_text())["messages"]
    assert exp.input_tokens(context) + 64 <= exp.cap
