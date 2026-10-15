"""Check experimental selection fidelity and the executable payment grader without providers."""

import pytest

from benchmark.compaction.repair_check import repair_checks
from benchmark.compaction.span_experiment import choose, evidence, noisy_variant, render

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


def test_ranked_selection_preserves_source_order_and_budget():
    """Ranking changes selection, not the order or bytes of retained evidence."""
    units = [{"id": str(i), "file": "x", "start": i * 10, "end": i * 10 + 3, "text": "abc"} for i in range(3)]
    limit = len(render([units[0], units[2]]))
    selected = choose(units, {"0": 0.8, "1": 0.1, "2": 0.9}, limit, len)
    assert selected == [units[0], units[2]]
    assert len(render(selected)) <= limit
    assert choose(units, dict.fromkeys(["0", "1", "2"], 0.5), 1, len) == []


def test_spans_reconstruct_exact_source_without_mutation():
    """Source offsets cover every byte of each textual observation, including the middle."""
    import json

    text = "routine line\n" * 130 + "important middle event\n" + "routine end\n" * 130
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
    units = evidence(messages)
    assert "".join(u["text"] for u in units) == text
    assert all(text[u["start"] : u["end"]] == u["text"] for u in units)
    assert json.dumps(messages) == before
    assert noisy_variant(messages) == messages


def test_fact_grading_rejects_wrong_nested_types():
    """Nested booleans/floats must not receive credit for integer counts or keys."""
    from copy import deepcopy

    from benchmark.compaction.run import GOLD, REPAIR, grade

    answer = {"facts": deepcopy(GOLD), "repair_plan": deepcopy(REPAIR)}
    assert all(grade(answer).values())
    answer["facts"]["regression_attempt_counts"]["validation_422"] = True
    answer["facts"]["no_retry_http_statuses"] = [402.0, 422.0]
    checks = grade(answer)
    assert not checks["facts.regression_attempt_counts"]
    assert not checks["facts.no_retry_http_statuses"]
    assert not any(grade([]).values())
