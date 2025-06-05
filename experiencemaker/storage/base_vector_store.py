from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.schema.vector_store_node import VectorStoreNode


class BaseVectorStore(BaseModel, ABC):
    embedding_model: BaseEmbeddingModel = Field(default=...)

    def insert(self, nodes: VectorStoreNode | List[VectorStoreNode], **kwargs):
        raise NotImplementedError

    def update(self, nodes: VectorStoreNode | List[VectorStoreNode], **kwargs):
        raise NotImplementedError

    def delete_by_id(self, unique_id: str, **kwargs):
        raise NotImplementedError

    def retrieve_by_id(self, unique_id: str, **kwargs) -> VectorStoreNode | None:
        raise NotImplementedError

    def retrieve_by_query(self, query: str, top_k: int = 3, **kwargs) -> List[VectorStoreNode]:
        raise NotImplementedError
