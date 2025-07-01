from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.experience import Experience
from experiencemaker.schema.trajectory import Trajectory, ContextMessage


class BaseResponse(BaseModel, ABC):
    success: bool = Field(default=True)
    metadata: dict = Field(default_factory=dict)

#
# class AgentWrapperResponse(BaseResponse):
#     trajectory: Trajectory = Field(default_factory=Trajectory)


class ContextGeneratorResponse(BaseResponse):
    experience: list[dict] = Field(default_factory=list)

    merge_experience: str = Field(default="")

    # when to use, experience, response




class SummarizerResponse(BaseResponse):
    experiences: List[dict] = Field(default_factory=list)
