import os
from typing import List
from pydantic import Field

from experiencemaker.schema.trajectory import Trajectory, Sample, SummaryMessage
from experiencemaker.storage.base_vector_store import BaseVectorStore
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from beyond.trajectory import Trajectory as TrajectoryOperation
from beyond.solver import TaskExecutor

class TrajectorySummarizer(BaseSummarizer):
    vector_store: BaseVectorStore | None = Field(default=None)
    samples: List[Sample] = Field(default=[])

    def extract_samples(self, trajectories: List[Trajectory], **kwargs) -> List[Sample]:
        raise NotImplementedError

    def insert_into_vector_store(self, samples: List[Sample], **kwargs):
        raise NotImplementedError

    def process_trajectory(self, traj: Trajectory):
        traj_operation = TrajectoryOperation()
        for step in traj.steps:
            step.executor = step.role.value
            traj_operation.raw_steps += [step]
        traj_description = traj_operation.chain_work_steps()
        mcp_url = os.getenv('MCP_URL', 'http://localhost:33333/sse')
        world_summary = traj_operation.generate_failure_ask_for_internet_help_raj_abs_post_level_3(mcp_url=mcp_url)
        self.samples += []

    def execute(self, trajectories: List[Trajectory], return_samples: bool = True, **kwargs) -> List[Sample]:
        for traj in trajectories:
            self.process_trajectory(traj)
        return self.samples
