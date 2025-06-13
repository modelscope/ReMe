from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.utils.registry import Registry

VECTOR_STORE_REGISTRY = Registry()

class BaseVectorStore(BaseModel, ABC):
    embedding_model: BaseEmbeddingModel = Field(default=...)
    index_name: str = Field(default=...)

    def exist_index(self, index_name: str = None) -> bool:
        raise NotImplementedError

    def delete_index(self, index_name: str = None):
        raise NotImplementedError

    def create_index(self, index_name: str = None):
        raise NotImplementedError

    def exist_id(self, unique_id: str, index_name: str = None):
        raise NotImplementedError

    def insert(self, nodes: VectorStoreNode | List[VectorStoreNode], index_name: str = None, **kwargs):
        raise NotImplementedError

    def update(self, nodes: VectorStoreNode | List[VectorStoreNode], index_name: str = None, **kwargs):
        raise NotImplementedError

    def delete_by_id(self, unique_id: str, index_name: str = None, **kwargs):
        raise NotImplementedError

    def retrieve_by_id(self, unique_id: str, index_name: str = None, **kwargs) -> VectorStoreNode | None:
        raise NotImplementedError

    def retrieve_by_query(self, query: str, top_k: int = 1, index_name: str = None, **kwargs) -> List[VectorStoreNode]:
        raise NotImplementedError
