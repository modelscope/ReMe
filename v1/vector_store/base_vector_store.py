from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from v1.model.base_embedding_model import BaseEmbeddingModel
from v1.schema.vector_node import VectorNode


class BaseVectorStore(BaseModel, ABC):
    embedding_model: BaseEmbeddingModel = Field(default=...)

    def exist_workspace(self, workspace_id: str, **kwargs) -> bool:
        raise NotImplementedError

    def delete_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def create_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def dump_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def load_workspace(self, workspace_id: str, **kwargs):
        raise NotImplementedError

    def retrieve_by_query(self, query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]:
        raise NotImplementedError

    def retrieve_by_id(self, unique_id: str, workspace_id: str = None, **kwargs) -> VectorNode | None:
        raise NotImplementedError

    def insert(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        raise NotImplementedError

    def update(self, nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs):
        raise NotImplementedError

    def exist_id(self, unique_id: str, workspace_id: str = None, **kwargs) -> bool:
        raise NotImplementedError

    def delete_id(self, unique_id: str, workspace_id: str = None, **kwargs):
        raise NotImplementedError
