from typing import List

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.schema.memory import BaseMemory, dict_to_memory


@C.register_op()
class UpdateMemoryFreqOp(BaseAsyncOp):
    file_path: str = __file__

    async def async_execute(self):
        memory_dicts: List[dict] = self.context.memory_dicts

        if not memory_dicts:
            logger.info("No memories to update freq")
            return

        memory_list: List[BaseMemory] = [dict_to_memory(memory_dict) for memory_dict in memory_dicts]
        new_memory_list = []
        deleted_memory_ids = []
        for memory in memory_list:
            # Update freq from metadata
            metadata = memory.metadata
            metadata["freq"] = metadata.get("freq", 0) + 1
            memory.update_metadata(metadata)

            deleted_memory_ids.append(memory.memory_id)
            new_memory_list.append(memory)

        self.context.deleted_memory_ids = deleted_memory_ids
        self.context.memory_list = new_memory_list
