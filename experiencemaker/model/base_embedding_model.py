from abc import ABC
from typing import List

from loguru import logger
from pydantic import BaseModel, Field

from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.utils.registry import Registry


class BaseEmbeddingModel(BaseModel, ABC):
    model_name: str = Field(default=..., description="model name")
    dimensions: int = Field(default=..., description="dimensions")
    max_retries: int = Field(default=3, description="max retries")
    raise_exception: bool = Field(default=True, description="raise exception")

    def _get_embeddings(self, input_text: str | List[str]):
        """
        Get the embedding vector based on the input text.
        This is an abstract method, and its concrete implementation must be provided in a subclass to generate the embedding vector for the given text.
        Args:
            input_text (str | List[str]): The input text, which can be a single string or a list of strings.
        Raises:
            NotImplementedError: If the method is not implemented in the subclass.
        """
        raise NotImplementedError

    def get_embeddings(self, input_text: str | List[str]):
        """
        Retrieves embeddings for the input text.

        This function attempts to obtain embeddings for the given input text. It will retry a maximum number of times in case of failure.

        Parameters:
        - input_text (str | List[str]): The input text, which can be a single string or a list of strings.

        Returns:
        - embeddings: The embeddings for the input text. Returns None if the maximum number of retries is reached and no successful result is obtained.
        """
        # Attempt to get embeddings, with a maximum number of retries set
        for i in range(self.max_retries):
            try:
                # Attempt to get embeddings, return immediately if successful
                return self._get_embeddings(input_text)

            except Exception as e:
                # Log exception information when an error occurs
                logger.exception(f"embedding model name={self.model_name} encounter error with e={e.args}")

                # If the maximum number of retries is reached and raise_exception is set to True, re-throw the exception
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e

        return None

    def get_node_embeddings(self, nodes: VectorStoreNode | List[VectorStoreNode]):
        """
        Assigns embeddings to the nodes based on their content.

        This function accepts either a single VectorStoreNode or a list of VectorStoreNodes.
        It retrieves the embedding for the content of each node and assigns it to the node's vector attribute.
        If a list of nodes is provided, it performs a batch retrieval of embeddings.

        Parameters:
        - nodes (VectorStoreNode | List[VectorStoreNode]): A single node or list of nodes whose embeddings need to be retrieved.

        Returns:
        - (VectorStoreNode | List[VectorStoreNode]): Returns the input nodes with their vector attribute populated with embeddings.

        Raises:
        - RuntimeError: If the input is neither a VectorStoreNode nor a list of VectorStoreNodes, a RuntimeError is raised.
        """
        if isinstance(nodes, VectorStoreNode):
            nodes.vector = self.get_embeddings(nodes.content)
            return nodes

        elif isinstance(nodes, list):
            embeddings = self.get_embeddings(input_text=[node.content for node in nodes])
            if len(embeddings) != len(nodes):
                logger.warning(f"embeddings.size={len(embeddings)} <> nodes.size={len(nodes)}")
            else:
                for node, embedding in zip(nodes, embeddings):
                    node.vector = embedding
            return nodes

        else:
            raise RuntimeError(f"unsupported type={type(nodes)}")


EMBEDDING_MODEL_REGISTRY = Registry[BaseEmbeddingModel]("embedding_model")
