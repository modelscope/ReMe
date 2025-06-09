from abc import ABC
from typing import List

from pydantic import Field, BaseModel

from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.schema.trajectory import Trajectory, ContextMessage
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore
from experiencemaker.utils.registry import Registry


class BaseContextGenerator(BaseModel, ABC):
    vector_store: BaseVectorStore | None = Field(default=None)
    llm: BaseLLM | None = Field(default=None)
    embedding_model: BaseEmbeddingModel | None = Field(default=None)
    workspace_id: str = Field(default="")

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


CONTEXT_GENERATOR_REGISTRY = Registry[BaseContextGenerator]("context_generator")
