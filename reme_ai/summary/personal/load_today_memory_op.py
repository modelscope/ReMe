from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.vector_node import VectorNode
from loguru import logger

from reme_ai.schema.memory import BaseMemory, vector_node_to_memory
from reme_ai.utils.datetime_handler import DatetimeHandler


@C.register_op()
class LoadTodayMemoryOp(BaseAsyncOp):
    """
    Operation to load today's memories from vector store for deduplication.
    Focuses specifically on retrieving and deduplicating memories from the current date.
    """
    file_path: str = __file__

    async def async_execute(self):
        """
        Load today's memories from vector store and perform deduplication.
        
        This operation:
        1. Retrieves memories from today using vector store search
        2. Converts vector nodes to memory objects
        3. Performs deduplication based on content similarity
        4. Stores deduplicated memories in context
        """
        # Get operation parameters
        top_k = self.op_params.get("top_k", 50)

        # Get required context values
        workspace_id = self.context.workspace_id
        user_name = self.context.get("user_name", "user")

        logger.info(f"Loading today's memories for user: {user_name} (top_k: {top_k})")

        # Get today's memories from vector store
        today_memories = await self._retrieve_today_memories(workspace_id, user_name, top_k)

        if not today_memories:
            logger.info("No memories found for today")
            self.context.today_memories = []
            return

        logger.info(f"Retrieved {len(today_memories)} memories from today")
        self.context.today_memories = today_memories
        logger.info(f"Final today's memory list size: {len(today_memories)}")

    async def _retrieve_today_memories(self, workspace_id: str, user_name: str, top_k: int) -> List[BaseMemory]:
        """
        Retrieve memories from today using vector store with date filtering.
        
        Args:
            workspace_id: Workspace identifier
            user_name: Target username
            top_k: Maximum number of memories to retrieve
            
        Returns:
            List of today's memories
        """
        try:
            # Get today's date for filtering
            dt_handler = DatetimeHandler()
            today_date = dt_handler.datetime_format().split()[0]  # Extract date part (YYYY-MM-DD)

            logger.info(f"Searching for memories from date: {today_date}")

            # Create filter criteria for today's memories
            filter_dict = {
                "memory_type": "personal",
                "target": user_name,
                "created_date": today_date
            }

            # Search vector store with date filter
            nodes: List[VectorNode] = await self.vector_store.async_search(
                query=" ",
                workspace_id=workspace_id,
                top_k=top_k,
                filter_dict=filter_dict)

            logger.info(f"Vector store returned {len(nodes)} nodes for today")

            # Convert vector nodes to memory objects
            memories = self._convert_nodes_to_memories(nodes)
            logger.info(f"Successfully converted {len(memories)} nodes to memories")

            return memories

        except Exception as e:
            logger.error(f"Error retrieving today's memories: {e}")
            return []

    @staticmethod
    def _convert_nodes_to_memories(nodes: List[VectorNode]) -> List[BaseMemory]:
        """
        Convert vector nodes to memory objects.
        
        Args:
            nodes: List of vector nodes from vector store
            
        Returns:
            List of converted memory objects
        """
        memories = []

        for i, node in enumerate(nodes):
            try:
                memory = vector_node_to_memory(node)
                memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to convert node {i} to memory: {e}")
                continue

        return memories
