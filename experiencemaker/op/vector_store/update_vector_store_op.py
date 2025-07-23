import json
from typing import List

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience
from experiencemaker.schema.request import BaseRequest
from experiencemaker.schema.vector_node import VectorNode


@OP_REGISTRY.register()
class UpdateVectorStoreOp(BaseOp):

    def execute(self):
        request: BaseRequest = self.context.request

        experience_ids: List[str] | None = self.context.response.deleted_experience_ids
        if experience_ids:
            self.vector_store.delete(node_ids=experience_ids, workspace_id=request.workspace_id)
            logger.info(f"delete experience_ids={json.dumps(experience_ids, indent=2)}")

        insert_experience_list: List[BaseExperience] | None = self.context.response.experience_list
        if insert_experience_list:
            insert_nodes: List[VectorNode] = [x.to_vector_node() for x in insert_experience_list]
            self.vector_store.insert(nodes=insert_nodes, workspace_id=request.workspace_id)
            logger.info(f"insert insert_node.size={len(insert_nodes)}")
