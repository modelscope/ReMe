from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.vector_node import VectorNode
from loguru import logger

from reme_ai.schema.memory import BaseMemory, vector_node_to_memory


@C.register_op()
class RetrieveMemoryOp(BaseAsyncOp):
    """
    Retrieves memories based on specified criteria such as status, type, and timestamp.
    Processes these memories concurrently, sorts them by similarity, and logs the activity,
    facilitating efficient memory retrieval operations within a given scope.
    """

    async def async_execute(self):
        recall_key: str = self.op_params.get("recall_key", "query")
        top_k: int = self.context.get("top_k", 3)

        query: str = self.context[recall_key]
        assert query, "query should be not empty!"

        workspace_id: str = self.context.workspace_id
        nodes: List[VectorNode] = await self.vector_store.async_search(query=query,
                                                                       workspace_id=workspace_id,
                                                                       top_k=top_k)
        memory_list: List[BaseMemory] = []
        memory_content_list: List[str] = []
        for node in nodes:
            memory: BaseMemory = vector_node_to_memory(node)
            if memory.content not in memory_content_list:
                memory_list.append(memory)
                memory_content_list.append(memory.content)
        logger.info(f"retrieve memory.size={len(memory_list)}")

        threshold_score: float | None = self.op_params.get("threshold_score", None)
        if threshold_score is not None:
            memory_list = [mem for mem in memory_list if mem.score >= threshold_score or mem.score is None]
            logger.info(f"after filter by threshold_score size={len(memory_list)}")

        self.context.response.metadata["memory_list"] = memory_list
