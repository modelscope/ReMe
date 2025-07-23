from abc import ABC
from typing import List

from loguru import logger
from pydantic import BaseModel, Field

from experiencemaker.schema.vector_node import VectorNode


class BaseEmbeddingModel(BaseModel, ABC):
    model_name: str = Field(default=..., description="model name")
    dimensions: int = Field(default=..., description="dimensions")
    max_retries: int = Field(default=3, description="max retries")
    raise_exception: bool = Field(default=True, description="raise exception")
    max_batch_size: int = Field(default=10, description="text-embedding-v4 batch size should not be larger than 10")

    def _get_embeddings(self, input_text: str | List[str]):
        raise NotImplementedError

    def get_embeddings(self, input_text: str | List[str]):
        for i in range(self.max_retries):
            try:
                return self._get_embeddings(input_text)

            except Exception as e:
                logger.exception(f"embedding model name={self.model_name} encounter error with e={e.args}")
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e

        return None

    def get_node_embeddings(self, nodes: VectorNode | List[VectorNode]):
        if isinstance(nodes, VectorNode):
            nodes.vector = self.get_embeddings(nodes.content)
            return nodes

        elif isinstance(nodes, list):

            embeddings = [emb for i in range(0, len(nodes), self.max_batch_size) for emb in
                          self.get_embeddings(input_text=[node.content for node in nodes[i:i + self.max_batch_size]])]
            if len(embeddings) != len(nodes):
                logger.warning(f"embeddings.size={len(embeddings)} <> nodes.size={len(nodes)}")
            else:
                for node, embedding in zip(nodes, embeddings):
                    node.vector = embedding
            return nodes

        else:
            raise RuntimeError(f"unsupported type={type(nodes)}")
