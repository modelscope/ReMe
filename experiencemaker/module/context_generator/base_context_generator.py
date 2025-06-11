from abc import ABC
from typing import List

from pydantic import Field, BaseModel

from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.schema.trajectory import Trajectory, ContextMessage
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore


class BaseContextGenerator(BaseModel, ABC):
    vector_store: BaseVectorStore | None = Field(default=None)
    llm: BaseLLM | None = Field(default=None)

    def _build_retrieve_query(self, trajectory: Trajectory, **kwargs) -> str:
        raise NotImplementedError

    def _retrieve_by_query(self, trajectory: Trajectory, query: str, workspace_id: str, retrieve_top_k: int,
                           **kwargs) -> List[VectorStoreNode]:
        raise NotImplementedError

    def _generate_context_message(self,
                                  trajectory: Trajectory,
                                  nodes: List[VectorStoreNode],
                                  **kwargs) -> ContextMessage:
        raise NotImplementedError

    def execute(self, trajectory: Trajectory, workspace_id: str = None, retrieve_top_k: int = 1,
                **kwargs) -> ContextMessage:
        query: str = self._build_retrieve_query(trajectory, **kwargs)
        nodes: List[VectorStoreNode] = self._retrieve_by_query(trajectory=trajectory,
                                                               query=query,
                                                               workspace_id=workspace_id,
                                                               retrieve_top_k=retrieve_top_k,
                                                               **kwargs)
        context_msg: ContextMessage = self._generate_context_message(trajectory, nodes, **kwargs)
        return context_msg
