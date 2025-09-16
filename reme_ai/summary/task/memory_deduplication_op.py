from typing import List

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class MemoryDeduplicationOp(BaseAsyncOp):
    file_path: str = __file__

    async def async_execute(self):
        """Remove duplicate task memories"""
        # Get task memories to deduplicate
        task_memories: List[BaseMemory] = self.context.memory_list

        if not task_memories:
            logger.info("No task memories found for deduplication")
            return

        logger.info(f"Starting deduplication for {len(task_memories)} task memories")

        # Perform deduplication
        deduplicated_task_memories = await self._deduplicate_task_memories(task_memories)

        logger.info(
            f"Deduplication complete: {len(deduplicated_task_memories)} deduplicated task memories out of {len(task_memories)}")

        # Update context
        self.context.memory_list = deduplicated_task_memories

    async def _deduplicate_task_memories(self, task_memories: List[BaseMemory]) -> List[BaseMemory]:
        """Remove duplicate task memories"""
        if not task_memories:
            return task_memories

        similarity_threshold = self.op_params.get("similarity_threshold", 0.5)
        workspace_id = self.context.get("workspace_id")

        unique_task_memories = []

        # Get existing task memory embeddings
        existing_embeddings = await self._get_existing_task_memory_embeddings(workspace_id)

        for task_memory in task_memories:
            # Generate embedding for current task memory
            current_embedding = self._get_task_memory_embedding(task_memory)

            if current_embedding is None:
                logger.warning(f"Failed to generate embedding for task memory: {str(task_memory.when_to_use)[:50]}...")
                continue

            # Check similarity with existing task memories
            if self._is_similar_to_existing_task_memories(current_embedding, existing_embeddings, similarity_threshold):
                logger.debug(f"Skipping similar task memory: {str(task_memory.when_to_use)[:50]}...")
                continue

            # Check similarity with current batch task memories
            if self._is_similar_to_current_task_memories(current_embedding, unique_task_memories, similarity_threshold):
                logger.debug(f"Skipping duplicate in current batch: {str(task_memory.when_to_use)[:50]}...")
                continue

            # Add to unique task memories list
            unique_task_memories.append(task_memory)
            logger.debug(f"Added unique task memory: {str(task_memory.when_to_use)[:50]}...")

        return unique_task_memories

    async def _get_existing_task_memory_embeddings(self, workspace_id: str) -> List[List[float]]:
        """Get embeddings of existing task memories"""
        try:
            if not hasattr(self.context, 'vector_store') or not self.context.vector_store or not workspace_id:
                return []

            # Query existing task memory nodes
            existing_nodes = await self.context.vector_store.async_search(
                query="...",  # Empty query to get all
                workspace_id=workspace_id,
                top_k=self.op_params.get("max_existing_task_memories", 1000)
            )

            # Extract embeddings
            existing_embeddings = []
            for node in existing_nodes:
                if hasattr(node, 'embedding') and node.embedding:
                    existing_embeddings.append(node.embedding)

            logger.debug(
                f"Retrieved {len(existing_embeddings)} existing task memory embeddings from workspace {workspace_id}")
            return existing_embeddings

        except Exception as e:
            logger.warning(f"Failed to retrieve existing task memory embeddings: {e}")
            return []

    def _get_task_memory_embedding(self, task_memory: BaseMemory) -> List[float] | None:
        """Generate embedding for task memory"""
        try:
            if not hasattr(self.context, 'vector_store') or not self.context.vector_store:
                return None

            # Combine task memory description and content for embedding
            text_for_embedding = f"{task_memory.when_to_use} {task_memory.content}"
            embeddings = self.context.vector_store.embedding_model.get_embeddings([text_for_embedding])

            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            else:
                logger.warning("Empty embedding generated for task memory")
                return None

        except Exception as e:
            logger.error(f"Error generating embedding for task memory: {e}")
            return None

    def _is_similar_to_existing_task_memories(self, current_embedding: List[float],
                                              existing_embeddings: List[List[float]],
                                              threshold: float) -> bool:
        """Check if current embedding is similar to existing embeddings"""
        for existing_embedding in existing_embeddings:
            similarity = self._calculate_cosine_similarity(current_embedding, existing_embedding)
            if similarity > threshold:
                logger.debug(f"Found similar existing task memory with similarity: {similarity:.3f}")
                return True
        return False

    def _is_similar_to_current_task_memories(self, current_embedding: List[float],
                                             current_task_memories: List[BaseMemory],
                                             threshold: float) -> bool:
        for existing_task_memory in current_task_memories:
            existing_embedding = self._get_task_memory_embedding(existing_task_memory)
            if existing_embedding is None:
                continue

            similarity = self._calculate_cosine_similarity(current_embedding, existing_embedding)
            if similarity > threshold:
                logger.debug(f"Found similar task memory in current batch with similarity: {similarity:.3f}")
                return True
        return False

    @staticmethod
    def _calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity"""
        try:
            import numpy as np

            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
