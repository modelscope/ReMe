from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from v1.schema.experience import BaseExperienceNode
from v1.schema.message import Message


class BaseResponse(BaseModel, ABC):
    success: bool = Field(default=True)
    metadata: dict = Field(default_factory=dict)


class RetrieverResponse(BaseResponse):
    experience_nodes: list[BaseExperienceNode] = Field(default_factory=list)
    experience_merged: str = Field(default="")


class SummarizerResponse(BaseResponse):
    experience_nodes: list[BaseExperienceNode] = Field(default_factory=list)


class VectorStoreResponse(BaseResponse):
    action: str = Field(default="")
    params: dict = Field(default_factory=dict)


class AgentResponse(BaseResponse):
    answer: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)
