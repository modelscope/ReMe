from abc import ABC
from typing import List

from loguru import logger
from pydantic import BaseModel, Field

from experiencemaker.schema.vector_node import VectorNode


class BaseEmbeddingModel(BaseModel, ABC):
    """
    Abstract base class for embedding models.
    
    This class provides a common interface for various embedding model implementations,
    including retry logic, error handling, and batch processing capabilities.
    """
    # Model configuration fields
    model_name: str = Field(default=..., description="Name of the embedding model")
    dimensions: int = Field(default=..., description="Dimensionality of the embedding vectors")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts on failure")
    raise_exception: bool = Field(default=True, description="Whether to raise exceptions after max retries")
    max_batch_size: int = Field(default=10, description="Maximum batch size for processing (text-embedding-v4 should not exceed 10)")

    def _get_embeddings(self, input_text: str | List[str]):
        """
        Abstract method to get embeddings from the model.
        
        This method must be implemented by concrete subclasses to provide
        the actual embedding functionality.
        
        Args:
            input_text: Single text string or list of text strings to embed
            
        Returns:
            Embedding vector(s) corresponding to the input text(s)
        """
        raise NotImplementedError

    def get_embeddings(self, input_text: str | List[str]):
        """
        Get embeddings with retry logic and error handling.
        
        This method wraps the _get_embeddings method with automatic retry
        functionality in case of failures.
        
        Args:
            input_text: Single text string or list of text strings to embed
            
        Returns:
            Embedding vector(s) or None if all retries failed and raise_exception is False
        """
        # Retry loop with exponential backoff potential
        for i in range(self.max_retries):
            try:
                return self._get_embeddings(input_text)

            except Exception as e:
                logger.exception(f"embedding model name={self.model_name} encounter error with e={e.args}")
                # If this is the last retry and raise_exception is True, re-raise the exception
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e

        # Return None if all retries failed and raise_exception is False
        return None

    def get_node_embeddings(self, nodes: VectorNode | List[VectorNode]):
        """
        Generate embeddings for VectorNode objects and update their vector fields.
        
        This method handles both single nodes and lists of nodes, with automatic
        batching for efficient processing of large node lists.
        
        Args:
            nodes: Single VectorNode or list of VectorNode objects to embed
            
        Returns:
            The same node(s) with updated vector fields containing embeddings
            
        Raises:
            RuntimeError: If unsupported node type is provided
        """
        # Handle single VectorNode
        if isinstance(nodes, VectorNode):
            nodes.vector = self.get_embeddings(nodes.content)
            return nodes

        # Handle list of VectorNodes with batch processing
        elif isinstance(nodes, list):
            # Process nodes in batches to respect max_batch_size limits
            embeddings = [emb for i in range(0, len(nodes), self.max_batch_size) for emb in
                          self.get_embeddings(input_text=[node.content for node in nodes[i:i + self.max_batch_size]])]
            
            # Validate that we got the expected number of embeddings
            if len(embeddings) != len(nodes):
                logger.warning(f"embeddings.size={len(embeddings)} <> nodes.size={len(nodes)}")
            else:
                # Assign embeddings to corresponding nodes
                for node, embedding in zip(nodes, embeddings):
                    node.vector = embedding
            return nodes

        else:  
            raise RuntimeError(f"unsupported type={type(nodes)}")
