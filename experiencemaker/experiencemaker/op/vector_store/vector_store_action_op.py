from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import vector_node_to_experience, dict_to_experience, BaseExperience
from experiencemaker.schema.request import VectorStoreRequest
from experiencemaker.schema.response import VectorStoreResponse
from experiencemaker.schema.vector_node import VectorNode


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
            def node_to_experience(node: VectorNode) -> dict:
                return vector_node_to_experience(node).model_dump()

            result = self.vector_store.dump_workspace(workspace_id=request.workspace_id,
                                                      path=request.path,
                                                      callback_fn=node_to_experience)

        elif request.action == "load":
            def experience_dict_to_node(experience_dict: dict) -> VectorNode:
                experience: BaseExperience = dict_to_experience(experience_dict=experience_dict)
                return experience.to_vector_node()

            result = self.vector_store.load_workspace(workspace_id=request.workspace_id,
                                                      path=request.path,
                                                      callback_fn=experience_dict_to_node)

        else:
            raise ValueError(f"invalid action={request.action}")

        if isinstance(result, dict):
            response.metadata.update(result)
        else:
            response.metadata["result"] = str(result)
