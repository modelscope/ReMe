from typing import List

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class UpdateMemoryUtilityOp(BaseAsyncOp):
    file_path: str = __file__

    async def async_execute(self):
        memory_dicts: List[dict] = self.context.memory_dicts
        update_utility = self.context.update_utility

        if not memory_dicts or not update_utility:
            logger.info("No memories to update utility")
            return

        memory_list: List[BaseMemory] = self.context.memory_list
        new_memory_list = []
        for memory in memory_list:
            # Update utility from metadata
            metadata = memory.metadata
            metadata["utility"] = metadata.get("utility", 0) + 1
            memory.update_metadata(metadata)

            new_memory_list.append(memory)

        self.context.response.metadata["memory_list"] = new_memory_list
        self.context.response.metadata["deleted_memory_ids"] = self.context.deleted_memory_ids
