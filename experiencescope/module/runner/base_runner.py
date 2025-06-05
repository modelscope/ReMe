from typing import List

from pydantic import BaseModel, Field

from experiencescope.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
from experiencescope.module.context_generator.base_context_generator import BaseContextGenerator
from experiencescope.module.environment.base_environment import BaseEnvironment
from experiencescope.module.summarizer.base_summarizer import BaseSummarizer
from experiencescope.schema.trajectory import Trajectory


class BaseRunner(BaseModel):
    agent_wrapper: BaseAgentWrapper | None = Field(default=None)
    context_generator: BaseContextGenerator | None = Field(default=None)
    summarizer: BaseSummarizer | None = Field(default=None)
    env: BaseEnvironment | None = Field(default=None)
    traj_buffer: List[Trajectory] = Field(default_factory=list)

    def reset(self):
        self.traj_buffer.clear()

    def rollout_trajectory(self, user_query: str, **kwargs):
        raise NotImplementedError

    def summary(self):
        raise NotImplementedError

    def start_backend_summary(self):
        raise NotImplementedError
