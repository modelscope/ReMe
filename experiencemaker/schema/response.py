from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.trajectory import Trajectory, ContextMessage, Sample


class BaseResponse(BaseModel, ABC):
    success: bool = Field(default=True)
    metadata: dict = Field(default_factory=dict)


class AgentWrapperResponse(BaseResponse):
    trajectory: Trajectory = Field(default_factory=Trajectory)


class ContextGeneratorResponse(BaseResponse):
    context_msg: ContextMessage = Field(default_factory=ContextMessage)


class SummarizerResponse(BaseResponse):
    extract_samples: List[Sample] = Field(default_factory=list)
