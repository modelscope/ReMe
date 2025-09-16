from typing import Iterable

from flowllm import C, BaseAsyncOp
from flowllm.schema.vector_node import VectorNode


@C.register_op()
class DeleteMemoryOp(BaseAsyncOp):
    file_path: str = __file__

    async def async_execute(self):
        workspace_id: str = self.context.workspace_id
        freq_threshold: int = self.context.freq_threshold
        utility_threshold: float = self.context.utility_threshold
        nodes: Iterable[VectorNode] = self.vector_store.iter_workspace_nodes(workspace_id=workspace_id)

        deleted_memory_ids = []
        for node in nodes:
            freq = node["metadata"]["metadata"]["freq"]
            utility = node["metadata"]["metadata"]["utility"]
            if freq >= freq_threshold:
                if utility * 1.0 / freq < utility_threshold:
                    deleted_memory_ids.append(node["unique_id"])

        self.context.deleted_memory_ids = deleted_memory_ids
