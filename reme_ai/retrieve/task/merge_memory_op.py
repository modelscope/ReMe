from typing import List

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class MergeMemoryOp(BaseAsyncOp):

    async def async_execute(self):
        memory_list: List[BaseMemory] = self.context.response.metadata["memory_list"]

        if not memory_list:
            return

        content_collector = ["Previous Memory"]
        for memory in memory_list:
            if not memory.content:
                continue

            content_collector.append(f"- {memory.when_to_use} {memory.content}\n")
        content_collector.append("Please consider the helpful parts from these in answering the question, "
                                 "to make the response more comprehensive and substantial.")
        self.context.response.answer = "\n".join(content_collector)
        logger.info(f"response.answer={self.context.response.answer}")
