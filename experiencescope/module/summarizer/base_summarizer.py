from typing import List

from pydantic import Field

from beyondagent.core.module.base_module import BaseModule
from beyondagent.core.schema.trajectory import Trajectory, Sample, SummaryMessage
from beyondagent.core.storage.base_vector_store import BaseVectorStore


class BaseSummarizer(BaseModule):
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


class MockSummarizer(BaseSummarizer):

    def execute(self, trajectories: List[Trajectory], return_samples: bool = True, **kwargs) -> List[Sample]:
        tip_message = SummaryMessage(content="I am a mock summarizer.")

        if return_samples:
            return [Sample(steps=[tip_message])]

        return []
