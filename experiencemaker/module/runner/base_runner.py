from typing import List

from pydantic import BaseModel, Field

from experiencemaker.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.module.environment.base_environment import BaseEnvironment
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from experiencemaker.schema.trajectory import Trajectory


class BaseRunner(BaseModel):
    agent_wrapper: BaseAgentWrapper | None = Field(default=None)
    context_generator: BaseContextGenerator | None = Field(default=None)
    summarizer: BaseSummarizer | None = Field(default=None)
    env: BaseEnvironment | None = Field(default=None)
    traj_buffer: List[Trajectory] = Field(default_factory=list)

    def reset(self):
        self.traj_buffer.clear()
        self.env.reset()

    def rollout_trajectory(self, query: str, **kwargs):
        raise NotImplementedError

    def summary(self, **kwargs):
        raise NotImplementedError