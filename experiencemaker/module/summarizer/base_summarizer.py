from abc import ABC
from typing import List

from pydantic import Field, BaseModel

from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.schema.experience import Experience
from experiencemaker.schema.trajectory import Trajectory
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.base_vector_store import BaseVectorStore


class BaseSummarizer(BaseModel, ABC):
    vector_store: BaseVectorStore | None = Field(default=None)
    llm: BaseLLM | None = Field(default=None)

    def _extract_experiences(self, trajectories: List[Trajectory], workspace_id: str = None,
                             **kwargs) -> List[Experience]:
        raise NotImplementedError

    def execute(self, trajectories: List[Trajectory], workspace_id: str = None, **kwargs) -> List[Experience]:
        experiences: List[Experience] = self._extract_experiences(trajectories, **kwargs)

        nodes: List[VectorStoreNode] = [x.to_vector_store_node() for x in experiences]
        self.vector_store.insert(nodes, index_name=workspace_id, **kwargs)

        return experiences
