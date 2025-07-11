from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.request import VectorStoreRequest
from experiencemaker.schema.response import VectorStoreResponse


@OP_REGISTRY.register()
class VectorStoreActionOp(BaseOp):

    def execute(self):
        request: VectorStoreRequest = self.context.request
        response: VectorStoreResponse = self.context.response

        if request.action == "copy":
            result = self.vector_store.copy_workspace(src_workspace_id=request.src_workspace_id,
                                                      dest_workspace_id=request.workspace_id)

        elif request.action == "delete":
            result = self.vector_store.delete_workspace(workspace_id=request.workspace_id)

        elif request.action == "dump":
            result = self.vector_store.dump_workspace(workspace_id=request.workspace_id,
                                                      path=request.path)

        elif request.action == "load":
            result = self.vector_store.load_workspace(workspace_id=request.workspace_id,
                                                      path=request.path)

        else:
            raise ValueError(f"invalid action={request.action}")

        if isinstance(result, dict):
            response.metadata.update(result)
        else:
            response.metadata["result"] = str(result)
