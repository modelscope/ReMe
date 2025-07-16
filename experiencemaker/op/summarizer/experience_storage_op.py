from typing import List
from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience
from experiencemaker.schema.vector_node import VectorNode


@OP_REGISTRY.register()
class ExperienceStorageOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        """Store experiences to vector database"""
        # Get experiences to store
        experiences: List[BaseExperience] = self.context.get_context("deduplicated_experiences", [])
        if not experiences:
            experiences = self.context.get_context("validated_experiences", [])
        if not experiences:
            experiences = self.context.get_context("extracted_experiences", [])
        
        if not experiences:
            logger.info("No experiences found for storage")
            return

        logger.info(f"Storing {len(experiences)} experiences to vector database")

        try:
            # Convert to vector storage nodes
            nodes: List[VectorNode] = [experience.to_vector_node() for experience in experiences]

            # Get workspace_id
            workspace_id = self.context.request.workspace_id if hasattr(self.context, 'request') else None
            if not workspace_id:
                workspace_id = self.op_params.get("default_workspace_id", "default")

            # Store to vector database
            if hasattr(self, 'vector_store') and self.vector_store:
                self.vector_store.insert(nodes, workspace_id=workspace_id)
                logger.info(f"Successfully stored {len(experiences)} experiences to workspace: {workspace_id}")
                
                # Set storage result to context
                self.context.set_context("storage_success", True)
                self.context.set_context("stored_count", len(experiences))
                
            else:
                logger.error("Vector store not available for storage")
                self.context.set_context("storage_success", False)
                self.context.set_context("storage_error", "Vector store not available")

            # Log stored experiences
            for experience in experiences:
                logger.info(f"Stored experience - Description: {str(experience.when_to_use)[:100]}...")

        except Exception as e:
            logger.error(f"Error storing experiences: {e}")
            self.context.set_context("storage_success", False)
            self.context.set_context("storage_error", str(e))