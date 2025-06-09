from abc import ABC
from typing import List

from pydantic import Field, BaseModel

from experiencemaker.schema.trajectory import Trajectory, Sample
from experiencemaker.storage.base_vector_store import BaseVectorStore


class BaseSummarizer(BaseModel, ABC):
    vector_store: BaseVectorStore | None = Field(default=None)

    def _extract_samples(self, trajectories: List[Trajectory], **kwargs) -> List[Sample]:
        raise NotImplementedError

    def _insert_into_database(self, samples: List[Sample], **kwargs):
        raise NotImplementedError

    def execute(self, trajectories: List[Trajectory], return_samples: bool = True, **kwargs) -> List[Sample]:
        samples: List[Sample] = self._extract_samples(trajectories, **kwargs)
        self._insert_into_database(samples, **kwargs)

        if return_samples:
            return samples

        return []