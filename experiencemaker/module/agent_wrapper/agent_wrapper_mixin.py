from abc import ABC

from pydantic import Field, BaseModel

from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.schema.trajectory import Trajectory
from experiencemaker.utils.registry import Registry


class AgentWrapperMixin(BaseModel, ABC):
    context_generator: BaseContextGenerator | None = Field(default=None)
    workspace_id: str = Field(default="")

    def execute(self, query: str, **kwargs) -> Trajectory:
        raise NotImplementedError


AGENT_WRAPPER_REGISTRY = Registry[AgentWrapperMixin]("agent_wrapper")
