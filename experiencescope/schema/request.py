from abc import ABC
from typing import List

from pydantic import Field

from experiencescope.schema.module_loader import ModuleLoader
from experiencescope.schema.trajectory import Trajectory


class BaseRequest(ModuleLoader, ABC):
    metadata: dict = Field(default_factory=dict)


class AgentWrapperRequest(BaseRequest):
    query: str = Field(default="")


class ContextGeneratorRequest(BaseRequest):
    trajectory: Trajectory = Field(default_factory=Trajectory)


class SummarizerRequest(BaseRequest):
    trajectories: List[Trajectory] = Field(default_factory=dict)
    return_samples: bool = Field(default=False)
