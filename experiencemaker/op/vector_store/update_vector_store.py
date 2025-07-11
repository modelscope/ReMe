import json
from typing import List

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.request import BaseRequest
from experiencemaker.schema.vector_node import VectorNode


@OP_REGISTRY.register()
class UpdateVectorStoreOp(BaseOp):
    INSERT_NODES = "insert_nodes"
    DELETE_NODE_IDS = "delete_node_ids"

    def execute(self):
        request: BaseRequest = self.context.request

        node_ids: List[str] | None = self.context.get_context(self.DELETE_NODE_IDS)
        if node_ids:
            self.vector_store.delete(node_ids=node_ids, workspace_id=request.workspace_id)
            logger.info(f"delete node_ids={json.dumps(node_ids, indent=2)}")

        insert_nodes: List[VectorNode] | None = self.context.get_context(self.INSERT_NODES)
        if insert_nodes:
            self.vector_store.insert(nodes=insert_nodes, workspace_id=request.workspace_id)
            for node in insert_nodes:
                logger.info(f"insert insert_node={node.model_dump_json(indent=2)}")
