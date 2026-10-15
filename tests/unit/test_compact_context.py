"""Compaction preserves source messages and fails atomically at provider boundaries."""

# pylint: disable=protected-access,redefined-outer-name
import asyncio
from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from reme.components import ApplicationContext
from reme.components.as_decision_model import BaseAsDecisionModel
from reme.components.job import BaseJob
from reme.enumeration import ComponentEnum
from reme.schema.compaction import CompactionOptions, CompactionRequest
from reme.steps.compaction import CompactContextStep
from reme.steps.compaction.messages import collect_pairs
from reme.steps.compaction.state import batch_questions, fit_state, estimate_decision_tokens


def transcript(count=3, output_size=2000):
    """Include same-message pairs and metadata that must survive rebuilding."""
    messages = [{"id": "first", "role": "user", "content": [{"type": "text", "text": "Keep paths exact."}]}]
    for i in range(count):
        messages.append(
            {
                "id": f"m{i}",
                "role": "assistant",
                "metadata": {"i": i},
                "content": [
                    {"type": "text", "text": f"Reading file {i}."},
                    {
                        "type": "tool_call",
                        "id": f"c{i}",
                        "name": "read_file",
                        "input": '{"path":"a.py"}',
                        "state": "finished",
                    },
                    {
                        "type": "tool_result",
                        "id": f"c{i}",
                        "name": "read_file",
                        "output": "x" * output_size,
                        "state": "success",
                        "metadata": {"source": "disk"},
                    },
                ],
            },
        )
    messages.append({"id": "last", "role": "user", "content": [{"type": "text", "text": "Now fix it."}]})
    return messages


class DecisionModel(BaseAsDecisionModel):
    """Fake binary provider with concurrency/cancellation observations."""

    def __init__(self, values=(0.9, 0.9), delay=0, fail=False, usage=None):
        super().__init__()
        self.values, self.delay, self.fail = values, delay, fail
        self.usage = usage
        self.calls, self.active, self.peak = [], 0, 0

    async def __call__(self, state, questions):
        self.calls.append((deepcopy(state), questions))
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            await asyncio.sleep(self.delay)
            if self.fail:
                raise RuntimeError("provider unavailable")
            content = {}
            for name in questions:
                index = int(name.split("_t")[1]) - 1
                values = self.values[index] if isinstance(self.values[0], tuple) else self.values
                content[name] = SimpleNamespace(
                    type="binary_answer",
                    probability=values[0 if name.startswith("call_") else 1],
                )
            return SimpleNamespace(content=content, usage=self.usage)
        finally:
            self.active -= 1


async def compact(messages, decision_model, **kwargs):
    """Use the real Step boundary and default to unprotected old read-only tools."""
    return await CompactContextStep(as_decision_model=decision_model)(
        messages=messages,
        eligible_tool_names=["read_file"],
        options={"preserve_recent_messages": 0, **kwargs},
    )


def test_three_actions_preserve_text_metadata_and_input():
    """Decisions only alter eligible tool blocks in the returned snapshot."""

    async def run():
        messages = transcript()
        original = deepcopy(messages)
        result = (await compact(messages, DecisionModel(((0.1, 0.9), (0.9, 0.1), (0.1, 0.1))))).answer
        assert messages == original
        assert [d["action"] for d in result["decisions"]] == ["keep", "drop_result", "drop_call"]
        assert result["messages"][1] == messages[1]
        shortened = result["messages"][2]["content"][-1]
        assert len(shortened["output"]) < 2000
        assert shortened["metadata"] == {"source": "disk"}
        assert result["messages"][3]["content"] == messages[3]["content"][:1]
        assert [m["metadata"] for m in result["messages"][1:-1]] == [{"i": i} for i in range(3)]
        assert result["changed"]

    asyncio.run(run())


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "running", "error", "media", "bad_input", "unknown"])
def test_uncertain_pairs_are_never_removed(mutation):
    """Ambiguous or unsafe pairs bypass classification."""

    async def run():
        messages = transcript(1)
        content = messages[1]["content"]
        if mutation == "duplicate":
            content.append(deepcopy(content[-1]))
        elif mutation == "missing":
            content.pop()
        elif mutation == "bad_input":
            content[1]["input"] = "invalid"
        elif mutation == "unknown":
            content[1]["name"] = "write_file"
        elif mutation == "media":
            content[-1]["output"] = [{"type": "data", "data": "image"}]
        else:
            content[-1]["state"] = mutation
        decision_model = DecisionModel((0, 0))
        result = (await compact(messages, decision_model)).answer
        assert not result["changed"]
        assert result["messages"] == messages
        assert not decision_model.calls

    asyncio.run(run())


def test_cross_message_pair_and_boundary_protection():
    """Protection of either endpoint protects the whole pair."""
    messages = transcript(1)
    result = messages[1]["content"].pop()
    messages.insert(2, {"id": "result", "role": "assistant", "content": [result]})
    request = CompactionRequest(
        messages=messages,
        eligible_tool_names=["read_file"],
        options={"preserve_recent_messages": 0},
    )
    assert not collect_pairs(request)[0].protected
    request.protected_message_ids = ["result"]
    assert collect_pairs(request)[0].protected
    request.protected_message_ids = []
    request.options.preserve_recent_messages = 2
    assert collect_pairs(request)[0].protected


def test_state_omits_outputs_thinking_and_fits_in_stages():
    """The observation view shrinks without disclosing outputs or thinking."""
    messages = transcript(8)
    messages[1]["content"].append({"type": "thinking", "thinking": "PRIVATE_THOUGHT"})
    messages[1]["content"][0]["text"] = "long text " * 3000
    request = CompactionRequest(
        messages=messages,
        eligible_tool_names=["read_file"],
        options={"preserve_recent_messages": 0, "max_state_tokens": 2500},
    )
    state, stage = fit_state(request, collect_pairs(request))
    assert stage != "inputs<=1000"
    assert estimate_decision_tokens(state) <= 2500
    assert "PRIVATE_THOUGHT" not in str(state)
    assert "x" * 100 not in str(state)
    request.options.max_state_tokens = 1
    with pytest.raises(ValueError, match="state budget"):
        fit_state(request, collect_pairs(request))


def test_batching_keeps_question_pairs_and_repeats_identical_state():
    """Question batching respects the request and concurrency budgets."""

    async def run():
        messages = transcript(18)
        request = CompactionRequest(
            messages=messages,
            eligible_tool_names=["read_file"],
            options={"preserve_recent_messages": 0},
        )
        state, _ = fit_state(request, collect_pairs(request))
        budget = estimate_decision_tokens({"state": state, "questions": {}}) + 600
        decision_model = DecisionModel(delay=0.001)
        await compact(messages, decision_model, max_request_tokens=budget, max_concurrency=2)
        assert len(decision_model.calls) > 1
        assert decision_model.peak <= 2
        assert all(call[0] == state for call in decision_model.calls)
        for _, questions in decision_model.calls:
            for name in questions:
                assert (
                    "result_" + name[5:] in questions if name.startswith("call_") else "call_" + name[7:] in questions
                )
        with pytest.raises(ValueError):
            batch_questions(state, collect_pairs(request), 1)

    asyncio.run(run())


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.1, 1.1, True, None])
def test_invalid_answers_fail_atomically(probability):
    """Invalid decision model probabilities cannot produce partial changes."""

    async def run():
        messages = transcript(2)
        original = deepcopy(messages)
        with pytest.raises(ExceptionGroup):
            await compact(messages, DecisionModel((probability, 0.1)))
        assert messages == original

    asyncio.run(run())


def test_timeout_and_external_cancellation_drain_requests():
    """Owned request tasks are drained on both timeout and cancellation."""

    async def run():
        decision_model = DecisionModel(delay=100)
        with pytest.raises(TimeoutError):
            await compact(transcript(), decision_model, total_timeout_seconds=0.01)
        assert decision_model.active == 0
        task = asyncio.create_task(compact(transcript(), decision_model))
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert decision_model.active == 0

    asyncio.run(run())


def test_real_job_registration_and_error_envelope(tmp_path):
    """The registered Step follows the standard Job error contract."""

    async def run():
        context = ApplicationContext(workspace_dir=str(tmp_path))
        context.components[ComponentEnum.AS_DECISION_MODEL] = {"default": DecisionModel(fail=True)}
        async with BaseJob(app_context=context, steps=[{"backend": "compact_context_step"}]) as job:
            response = await job(
                messages=transcript(),
                eligible_tool_names=["read_file"],
                options={"preserve_recent_messages": 0},
            )
            assert not response.success
            assert isinstance(response.answer, str)
        response = await CompactContextStep()(messages=transcript())
        assert response.success and response.answer["reason"] == "no_candidates"

    asyncio.run(run())


@pytest.mark.parametrize(
    "options",
    [{"keep_threshold": float("nan")}, {"max_concurrency": 0}, {"truncate_head_chars": -1}, {"surprise": 1}],
)
def test_invalid_options(options):
    """Invalid options fail before any network call."""
    with pytest.raises(ValidationError):
        CompactionOptions(**options)


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_nonfinite_tool_inputs_preserve_pair_without_blocking_valid_candidates(number):
    """Malformed tool inputs neither reach the provider nor poison other pairs."""

    async def run():
        messages = transcript(2)
        messages[1]["content"][1]["input"] = '{"value":' + number + "}"
        original = deepcopy(messages)
        decision_model = DecisionModel((0, 0))
        result = (await compact(messages, decision_model)).answer
        assert messages == original
        assert result["messages"][1] == original[1]
        assert [decision["call_id"] for decision in result["decisions"]] == ["c1"]
        assert result["stats"]["candidates"] == 1
        assert len(decision_model.calls) == 1
        state = decision_model.calls[0][0]
        assert state["history"][1]["tool_calls"] == []

    asyncio.run(run())


@dataclass
class _Usage:
    """Usage from a provider that returns dataclass records."""

    input_tokens: int = 12
    output_tokens: int = 2


@pytest.mark.parametrize("usage", [{"input_tokens": 12, "output_tokens": 2}, _Usage()])
def test_usage_accepts_json_objects_and_dataclasses(usage):
    """Compaction supports either usage representation in the generic contract."""

    async def run():
        result = (await compact(transcript(1), DecisionModel(usage=usage))).answer
        assert result["stats"]["usage"] == [{"input_tokens": 12, "output_tokens": 2}]

    asyncio.run(run())
