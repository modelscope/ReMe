import json
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.vector_node import VectorNode
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class UpdateVectorStoreOp(BaseAsyncOp):

    async def async_execute(self):
        workspace_id: str = self.context.workspace_id

        deleted_memory_ids: List[str] = self.context.response.metadata.get("deleted_memory_ids", [])
        if deleted_memory_ids:
            await self.vector_store.async_delete(node_ids=deleted_memory_ids, workspace_id=workspace_id)
            logger.info(f"delete memory_ids={json.dumps(deleted_memory_ids, indent=2)}")

        insert_memory_list: List[BaseMemory] = self.context.response.metadata.get("memory_list", [])
        if insert_memory_list:
            insert_nodes: List[VectorNode] = [x.to_vector_node() for x in insert_memory_list]
            await self.vector_store.async_insert(nodes=insert_nodes, workspace_id=workspace_id)
            logger.info(f"insert insert_node.size={len(insert_nodes)}")

        # Store results in context
        self.context.response.metadata["update_result"] = {
            "deleted_count": len(deleted_memory_ids) if deleted_memory_ids else 0,
            "inserted_count": len(insert_memory_list) if insert_memory_list else 0
        }
