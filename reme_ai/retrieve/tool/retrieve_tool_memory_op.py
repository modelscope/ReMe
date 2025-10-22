from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.vector_node import VectorNode
from loguru import logger

from reme_ai.schema.memory import ToolMemory, vector_node_to_memory


@C.register_op()
class RetrieveToolMemoryOp(BaseAsyncOp):
    file_path: str = __file__

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def async_execute(self):
        tool_names: str = self.context.get("tool_names", "")
        workspace_id: str = self.context.workspace_id

        if not tool_names:
            logger.warning("tool_names is empty, skipping processing")
            self.context.response.answer = "tool_names is required"
            self.context.response.success = False
            return

        # Split tool names by comma
        tool_name_list = [name.strip() for name in tool_names.split(",") if name.strip()]
        logger.info(f"workspace_id={workspace_id} retrieving {len(tool_name_list)} tools: {tool_name_list}")

        # Search for each tool in the vector store
        matched_tool_memories: List[ToolMemory] = []

        for tool_name in tool_name_list:
            nodes: List[VectorNode] = await self.vector_store.async_search(
                query=tool_name,
                workspace_id=workspace_id,
                top_k=1
            )

            if nodes:
                top_node = nodes[0]
                memory = vector_node_to_memory(top_node)

                # Ensure it's a ToolMemory and when_to_use matches
                if isinstance(memory, ToolMemory) and memory.when_to_use == tool_name:
                    matched_tool_memories.append(memory)
                    logger.info(f"Found tool_memory for tool_name={tool_name}, "
                                f"memory_id={memory.memory_id}, "
                                f"total_calls={len(memory.tool_call_results)}")
                else:
                    logger.warning(f"No exact match found for tool_name={tool_name}")
            else:
                logger.warning(f"No memory found for tool_name={tool_name}")

        if not matched_tool_memories:
            logger.info("No matching tool memories found")
            self.context.response.answer = "No matching tool memories found"
            self.context.response.success = False
            return

        # Set response
        self.context.response.answer = f"Successfully retrieved {len(matched_tool_memories)} tool memories"
        self.context.response.success = True
        self.context.response.metadata["memory_list"] = matched_tool_memories

        # Log retrieval results
        for memory in matched_tool_memories:
            logger.info(f"Retrieved tool: {memory.when_to_use}, "
                        f"total_calls={len(memory.tool_call_results)}, "
                        f"content_length={len(memory.content)}")
