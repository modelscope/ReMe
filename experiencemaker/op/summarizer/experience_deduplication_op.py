from typing import List
from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience


@OP_REGISTRY.register()
class ExperienceDeduplicationOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        """Remove duplicate experiences"""
        # Get experiences to deduplicate
        experiences: List[BaseExperience] = self.context.response.experience_list

        if not experiences:
            logger.info("No experiences found for deduplication")
            return

        logger.info(f"Starting deduplication for {len(experiences)} experiences")

        # Perform deduplication
        deduplicated_experiences = self._deduplicate_experiences(experiences)

        logger.info(f"Deduplication complete: {len(deduplicated_experiences)} deduplicated experiences out of {len(experiences)}")
        
        # Update context
        self.context.response.experience_list = deduplicated_experiences

    def _deduplicate_experiences(self, experiences: List[BaseExperience]) -> List[BaseExperience]:
        """Remove duplicate experiences"""
        if not experiences:
            return experiences

        similarity_threshold = self.op_params.get("similarity_threshold", 0.5)
        workspace_id = self.context.request.workspace_id if hasattr(self.context, 'request') else None

        unique_experiences = []

        # Get existing experience embeddings
        existing_embeddings = self._get_existing_experience_embeddings(workspace_id)

        for experience in experiences:
            # Generate embedding for current experience
            current_embedding = self._get_experience_embedding(experience)

            if current_embedding is None:
                logger.warning(f"Failed to generate embedding for experience: {str(experience.when_to_use)[:50]}...")
                continue

            # Check similarity with existing experiences
            if self._is_similar_to_existing_experiences(current_embedding, existing_embeddings, similarity_threshold):
                logger.debug(f"Skipping similar experience: {str(experience.when_to_use)[:50]}...")
                continue

            # Check similarity with current batch experiences
            if self._is_similar_to_current_experiences(current_embedding, unique_experiences, similarity_threshold):
                logger.debug(f"Skipping duplicate in current batch: {str(experience.when_to_use)[:50]}...")
                continue

            # Add to unique experiences list
            unique_experiences.append(experience)
            logger.debug(f"Added unique experience: {str(experience.when_to_use)[:50]}...")

        return unique_experiences

    def _get_existing_experience_embeddings(self, workspace_id: str) -> List[List[float]]:
        """Get embeddings of existing experiences"""
        try:
            if not hasattr(self, 'vector_store') or not self.vector_store or not workspace_id:
                return []

            # Query existing experience nodes
            existing_nodes = self.vector_store.search(
                query="...",  # Empty query to get all
                workspace_id=workspace_id,
                top_k=self.op_params.get("max_existing_experiences", 1000)
            )

            # Extract embeddings
            existing_embeddings = []
            for node in existing_nodes:
                if hasattr(node, 'embedding') and node.embedding:
                    existing_embeddings.append(node.embedding)

            logger.debug(f"Retrieved {len(existing_embeddings)} existing experience embeddings from workspace {workspace_id}")
            return existing_embeddings

        except Exception as e:
            logger.warning(f"Failed to retrieve existing experience embeddings: {e}")
            return []

    def _get_experience_embedding(self, experience: BaseExperience) -> List[float]:
        """Generate embedding for experience"""
        try:
            if not hasattr(self, 'vector_store') or not self.vector_store:
                return None

            # Combine experience description and content for embedding
            text_for_embedding = f"{experience.when_to_use} {experience.content}"
            embeddings = self.vector_store.embedding_model.get_embeddings([text_for_embedding])

            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            else:
                logger.warning("Empty embedding generated for experience")
                return None

        except Exception as e:
            logger.error(f"Error generating embedding for experience: {e}")
            return None


    def _is_similar_to_existing_experiences(self, current_embedding: List[float],
                                          existing_embeddings: List[List[float]],
                                          threshold: float) -> bool:
        """Check if current embedding is similar to existing embeddings"""
        for existing_embedding in existing_embeddings:
            similarity = self._calculate_cosine_similarity(current_embedding, existing_embedding)
            if similarity > threshold:
                logger.debug(f"Found similar existing experience with similarity: {similarity:.3f}")
                return True
        return False

    def _is_similar_to_current_experiences(self, current_embedding: List[float],
                                         current_experiences: List[BaseExperience],
                                         threshold: float) -> bool:
        for existing_experience in current_experiences:
            existing_embedding = self._get_experience_embedding(existing_experience)
            if existing_embedding is None:
                continue

            similarity = self._calculate_cosine_similarity(current_embedding, existing_embedding)
            if similarity > threshold:
                logger.debug(f"Found similar experience in current batch with similarity: {similarity:.3f}")
                return True
        return False

    def _calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
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