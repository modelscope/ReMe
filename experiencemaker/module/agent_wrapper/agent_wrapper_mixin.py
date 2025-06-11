from abc import ABC

from pydantic import Field, BaseModel

from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.schema.trajectory import Trajectory


class AgentWrapperMixin(BaseModel, ABC):
    context_generator: BaseContextGenerator | None = Field(default=None)
    llm: BaseLLM | None = Field(default=None)

    def execute(self, query: str, workspace_id: str = None, **kwargs) -> Trajectory:
        raise NotImplementedError
