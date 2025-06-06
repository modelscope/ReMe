from typing import List

from pydantic import Field

from experiencemaker.schema.trajectory import Trajectory, Sample, SummaryMessage
from experiencemaker.storage.base_vector_store import BaseVectorStore
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer

class TrajectorySummarizer(BaseSummarizer):
    vector_store: BaseVectorStore | None = Field(default=None)

    def extract_samples(self, trajectories: List[Trajectory], **kwargs) -> List[Sample]:
        raise NotImplementedError

    def insert_into_vector_store(self, samples: List[Sample], **kwargs):
        raise NotImplementedError

    def execute(self, trajectories: List[Trajectory], return_samples: bool = True, **kwargs) -> List[Sample]:
        samples: List[Sample] = self.extract_samples(trajectories, **kwargs)
        self.insert_into_vector_store(samples, **kwargs)

        if return_samples:
            return samples

        return []

