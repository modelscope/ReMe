from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.trajectory import Trajectory


class BaseRequest(BaseModel, ABC):
    metadata: dict = Field(default_factory=dict)


class AgentWrapperRequest(BaseRequest):
    query: str = Field(default="")


class ContextGeneratorRequest(BaseRequest):
    trajectory: Trajectory = Field(default_factory=Trajectory)


class SummarizerRequest(BaseRequest):
    trajectories: List[Trajectory] = Field(default_factory=dict)
    return_experience: bool = Field(default=True)
