from flowllm import C, BaseAsyncOp
from flowllm.schema.vector_node import VectorNode

from reme_ai.schema.memory import vector_node_to_memory, dict_to_memory, BaseMemory


@C.register_op()
class VectorStoreActionOp(BaseAsyncOp):

    async def async_execute(self):
        workspace_id: str = self.context.workspace_id
        action: str = self.context.action
        result = ""
        if action == "copy":
            src_workspace_id: str = self.context.src_workspace_id
            result = await self.vector_store.async_copy_workspace(src_workspace_id=src_workspace_id,
                                                                  dest_workspace_id=workspace_id)

        elif action == "delete":
            if await self.vector_store.async_exist_workspace(workspace_id):
                result = await self.vector_store.async_delete_workspace(workspace_id=workspace_id)

        elif action == "delete_ids":
            memory_ids: list = self.context.memory_ids
            result = await self.vector_store.async_delete(workspace_id=workspace_id, node_ids=memory_ids)

        elif action == "dump":
            path: str = self.context.path

            def node_to_memory(node: VectorNode) -> dict:
                return vector_node_to_memory(node).model_dump()

            result = await self.vector_store.async_dump_workspace(workspace_id=workspace_id,
                                                                  path=path,
                                                                  callback_fn=node_to_memory)

        elif action == "list":
            def node_to_memory(node: VectorNode) -> dict:
                return vector_node_to_memory(node).model_dump()

            result = await self.vector_store.async_iter_workspace_nodes(workspace_id=workspace_id)
            result = [node_to_memory(node) for node in result]

        elif action == "load":
            path: str = self.context.path

            def memory_dict_to_node(memory_dict: dict) -> VectorNode:
                memory: BaseMemory = dict_to_memory(memory_dict=memory_dict)
                return memory.to_vector_node()

            result = await self.vector_store.async_load_workspace(workspace_id=workspace_id,
                                                                  path=path,
                                                                  callback_fn=memory_dict_to_node)

        else:
            raise ValueError(f"invalid action={action}")

        self.context.response.metadata["action_result"] = result
