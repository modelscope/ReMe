from flowllm import C, BaseLLMOp
from flowllm.schema.vector_node import VectorNode

from reme_ai.schema.memory import vector_node_to_memory, dict_to_memory, BaseMemory


@C.register_op()
class VectorStoreActionOp(BaseLLMOp):

    def execute(self):
        workspace_id: str = self.context.workspace_id
        action: str = self.context.action

        if action == "copy":
            src_workspace_id: str = self.context.src_workspace_id
            result = self.vector_store.copy_workspace(src_workspace_id=src_workspace_id,
                                                      dest_workspace_id=workspace_id)

        elif action == "delete":
            if self.vector_store.exist_workspace(workspace_id):
                result = self.vector_store.delete_workspace(workspace_id=workspace_id)

        elif action == "delete_ids":
            memory_ids: list = self.context.memory_ids
            result = self.vector_store.delete(workspace_id=workspace_id, node_ids=memory_ids)

        elif action == "dump":
            path: str = self.context.path

            def node_to_memory(node: VectorNode) -> dict:
                return vector_node_to_memory(node).model_dump()

            result = self.vector_store.dump_workspace(workspace_id=workspace_id,
                                                      path=path,
                                                      callback_fn=node_to_memory)

        elif action == "load":
            path: str = self.context.path

            def memory_dict_to_node(memory_dict: dict) -> VectorNode:
                memory: BaseMemory = dict_to_memory(memory_dict=memory_dict)
                return memory.to_vector_node()

            result = self.vector_store.load_workspace(workspace_id=workspace_id,
                                                      path=path,
                                                      callback_fn=memory_dict_to_node)

        else:
            raise ValueError(f"invalid action={action}")

        # Store results in context
        if isinstance(result, dict):
            self.context.response.metadata["action_result"] = result
        else:
            self.context.response.metadata["action_result"] = {"result": str(result)}
