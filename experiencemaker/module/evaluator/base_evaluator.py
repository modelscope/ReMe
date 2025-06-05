from abc import ABC

from pydantic import BaseModel, Field

from experiencemaker.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.module.environment.base_environment import BaseEnvironment
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer


class BaseEvaluator(BaseModel, ABC):
    data_path: str = Field(default="")
    agent_wrapper: BaseAgentWrapper | None = Field(default=None)
    context_generator: BaseContextGenerator | None = Field(default=None)
    summarizer: BaseSummarizer | None = Field(default=None)
    env: BaseEnvironment | None = Field(default=None)

    def evaluate(self, **kwargs):
        raise NotImplementedError
