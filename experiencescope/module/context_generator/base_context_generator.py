from abc import ABC
from typing import List

from pydantic import Field

from beyondagent.core.module.base_module import BaseModule
from beyondagent.core.schema.trajectory import Trajectory, ContextMessage
from beyondagent.core.schema.vector_store_node import VectorStoreNode
from beyondagent.core.storage.base_vector_store import BaseVectorStore


class BaseContextGenerator(BaseModule, ABC):
    vector_store: BaseVectorStore | None = Field(default=None)

    def _build_retrieve_query(self, trajectory: Trajectory, **kwargs) -> str:
        raise NotImplementedError

    def _retrieve_by_query(self, trajectory: Trajectory, query: str, **kwargs) -> List[VectorStoreNode]:
        raise NotImplementedError

    def _generate_context_message(self,
                                 trajectory: Trajectory,
                                 nodes: List[VectorStoreNode],
                                 **kwargs) -> ContextMessage:
        raise NotImplementedError

    def execute(self, trajectory: Trajectory, **kwargs) -> ContextMessage:
        query: str = self._build_retrieve_query(trajectory, **kwargs)
        nodes: List[VectorStoreNode] = self._retrieve_by_query(trajectory, query, **kwargs)
        context_msg: ContextMessage = self._generate_context_message(trajectory, nodes, **kwargs)
        return context_msg


class MockContextGenerator(BaseContextGenerator):

    def execute(self, trajectory: Trajectory, **kwargs) -> ContextMessage:
        return ContextMessage(content="mock context")
