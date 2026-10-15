"""A lifecycle-neutral Job Step proposing tool-history compaction."""

import asyncio
from dataclasses import asdict, is_dataclass
import math
import time

from ..base_step import BaseStep, Ref
from ...components import R
from ...components.as_decision_model import BaseAsDecisionModel
from ...enumeration import ComponentEnum
from ...schema.compaction import CallDecision, CompactionRequest, CompactionResult
from .messages import apply_decisions, collect_pairs
from .state import batch_questions, fit_state, serialize, estimate_decision_tokens


@R.register("compact_context_step")
class CompactContextStep(BaseStep):
    """All batches must succeed before any proposed changes are returned."""

    as_decision_model = Ref(BaseAsDecisionModel, ComponentEnum.AS_DECISION_MODEL)

    async def execute(self):
        started = time.monotonic()
        request = CompactionRequest.model_validate(
            {key: self.context[key] for key in CompactionRequest.model_fields if key in self.context},
        )
        pairs = collect_pairs(request)
        candidates = [pair for pair in pairs if not pair.protected]
        answers, usage = {}, []
        batches, state, stage = [], {}, ""
        if candidates:
            state, stage = fit_state(request, pairs)
            batches = batch_questions(state, candidates, request.options.max_request_tokens)
            semaphore = asyncio.Semaphore(request.options.max_concurrency)

            async def ask(questions):
                async with semaphore:
                    response = await self.as_decision_model(state=state, questions=questions)
                probabilities = {}
                for name in questions:
                    answer = response.content.get(name)
                    value = getattr(answer, "probability", None)
                    if (
                        getattr(answer, "type", None) != "binary_answer"
                        or isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                        or not 0 <= value <= 1
                    ):
                        raise ValueError("Decision model returned an invalid binary answer.")
                    probabilities[name] = value
                if response.usage is not None:
                    usage.append(asdict(response.usage) if is_dataclass(response.usage) else response.usage)
                answers.update(probabilities)

            async with asyncio.timeout(request.options.total_timeout_seconds):
                async with asyncio.TaskGroup() as tasks:
                    for batch in batches:
                        tasks.create_task(ask(batch))
        decisions = []
        for pair in pairs:
            if pair.protected:
                decisions.append(CallDecision(id=pair.id, call_id=pair.call_id, action="keep", reason="protected"))
                continue
            call, result = answers[f"call_{pair.id}"], answers[f"result_{pair.id}"]
            threshold = request.options.keep_threshold
            action = "keep" if result >= threshold else "drop_result" if call >= threshold else "drop_call"
            decisions.append(
                CallDecision(
                    id=pair.id,
                    call_id=pair.call_id,
                    action=action,
                    reason=action,
                    keep_call=call,
                    keep_result=result,
                ),
            )
        messages = apply_decisions(request.messages, pairs, decisions, request.options.truncate_head_chars)
        changed = messages != request.messages
        stats = {
            "messages_before": len(request.messages),
            "messages_after": len(messages),
            "chars_before": len(serialize(request.messages)),
            "chars_after": len(serialize(messages)),
            "candidates": len(candidates),
            "protected": len(pairs) - len(candidates),
            "state_tokens": estimate_decision_tokens(state) if batches else 0,
            "state_stage": stage,
            "requests": len(batches),
            "usage": usage,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }
        result = CompactionResult(
            messages=messages,
            decisions=decisions,
            changed=changed,
            reason="compacted" if changed else "no_change" if candidates else "no_candidates",
            stats=stats,
        )
        self.context.response.answer = result.model_dump(mode="json")
        self.context.response.metadata["compaction"] = stats
        return self.context.response
