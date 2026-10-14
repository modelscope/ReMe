"""Classifier demo wiring and JSON output without optional SDK dependencies."""

import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from reme.components.application_context import ApplicationContext
from reme.components.as_classifier import BaseAsClassifier
from reme.components.job import BaseJob
from reme.components.runtime_context import RuntimeContext
from reme.enumeration import ComponentEnum
from reme.steps.base_step import BaseStep
from reme.steps.common.classifier_demo import ClassifierDemoStep


@dataclass
class _Result:
    """Small classifier-response stand-in for Step boundary tests."""

    model: str = "jev-test"
    content: dict = field(
        default_factory=lambda: {
            "urgent": {"type": "binary_answer", "probability": 0.8},
            "priority": {"type": "score_answer", "score": 0.7, "legend": {0: "low", 1: "high"}},
        },
    )
    usage: dict = field(default_factory=lambda: {"input_tokens": 12, "output_tokens": 2})


class _Classifier(BaseAsClassifier):
    """Recording component accepting the same inputs as a provider."""

    def __init__(self):
        super().__init__()
        self.call = AsyncMock(return_value=_Result())

    async def __call__(self, state, questions):
        return await self.call(state=state, questions=questions)


def test_demo_serializes_complete_result_and_preserves_context():
    """The answer is JSON-ready and available to later Steps in the same request."""

    async def run():
        classifier = _Classifier()
        step = ClassifierDemoStep(as_classifier=classifier)
        context = RuntimeContext(state="I was charged twice.", keep="original")
        context.response.metadata["earlier"] = True
        response = await step(context)
        assert response.success
        assert response.answer["model"] == "jev-test"
        assert response.answer["content"]["urgent"]["probability"] == 0.8
        assert response.answer["content"]["priority"]["legend"] == {"0": "low", "1": "high"}
        assert response.answer["usage"]["input_tokens"] == 12
        assert context.data["classifier_result"] is response.answer
        assert context.data["keep"] == "original"
        assert response.metadata == {"earlier": True}
        assert {q["type"] for q in classifier.call.await_args.kwargs["questions"].values()} == {
            "binary",
            "choice",
            "score",
        }

    asyncio.run(run())


@pytest.mark.parametrize("questions", [{"custom": {"type": "binary"}}, {}, None])
def test_explicit_questions_replace_defaults(questions):
    """Even invalid explicit values reach component validation rather than demo fallback."""

    async def run():
        classifier = _Classifier()
        await ClassifierDemoStep(as_classifier=classifier)(state={"request": "hello"}, questions=questions)
        assert classifier.call.await_args.kwargs["questions"] == questions

    asyncio.run(run())


def test_ref_uses_named_component_and_clears_between_calls(tmp_path):
    """Reusing a standalone Step respects each request's component selection."""

    async def run():
        context = ApplicationContext(workspace_dir=str(tmp_path))
        first, second = _Classifier(), _Classifier()
        context.components[ComponentEnum.AS_CLASSIFIER] = {"first": first, "second": second}
        step = ClassifierDemoStep(app_context=context)
        await step(state="hello", as_classifier="first")
        await step(state="hello", as_classifier="second")
        first.call.assert_awaited_once()
        second.call.assert_awaited_once()

    asyncio.run(run())


def test_job_shares_result_and_rebuilds_steps(tmp_path):
    """Sequential Steps see classifier data, and no result leaks across invocations."""

    class ConsumeResultStep(BaseStep):
        """Read the prior Step's output using the ordinary request context."""

        async def execute(self):
            self.context.response.metadata["consumer_model"] = self.context.data["classifier_result"]["model"]

    async def run():
        context = ApplicationContext(workspace_dir=str(tmp_path))
        classifier = _Classifier()
        context.components[ComponentEnum.AS_CLASSIFIER] = {"default": classifier}
        context.registry.add("consume_classifier_result", ConsumeResultStep, owner="test")
        job = BaseJob(
            app_context=context,
            steps=[
                {"backend": "classifier_demo_step"},
                {"backend": "consume_classifier_result"},
            ],
        )
        async with job:
            first = await job(state="first")
            second = await job(state="second")
        assert first.success and second.success
        assert first.metadata["consumer_model"] == "jev-test"
        assert first.answer is not second.answer
        assert [call.kwargs["state"] for call in classifier.call.await_args_list] == ["first", "second"]

    asyncio.run(run())


def test_job_converts_provider_error_to_failed_response(tmp_path):
    """SDK errors follow the existing BaseJob error contract."""

    async def run():
        context = ApplicationContext(workspace_dir=str(tmp_path))
        classifier = _Classifier()
        classifier.call.side_effect = TimeoutError("classifier timed out")
        context.components[ComponentEnum.AS_CLASSIFIER] = {"default": classifier}
        async with BaseJob(app_context=context, steps=[{"backend": "classifier_demo_step"}]) as job:
            response = await job(state="hello")
        assert not response.success
        assert "classifier timed out" in response.answer

    asyncio.run(run())
