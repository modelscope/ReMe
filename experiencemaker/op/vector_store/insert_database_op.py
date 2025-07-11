from typing import List

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.vector_node import VectorNode


@OP_REGISTRY.register()
class InsertDatabaseOp(BaseOp):
    INSERT_NODES: str = "insert_nodes"

    def execute(self):
        nodes: List[VectorNode] = self.context.get_context(InsertDatabaseOp.INSERT_NODES)
        self.vector_store.insert(nodes=nodes, workspace_id=self.context.request.workspace_id)



