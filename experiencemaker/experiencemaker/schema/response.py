from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.experience import BaseExperience
from experiencemaker.schema.message import Message


class BaseResponse(BaseModel):
    success: bool = Field(default=True)
    metadata: dict = Field(default_factory=dict)


class RetrieverResponse(BaseResponse):
    experience_list: List[BaseExperience] = Field(default_factory=list)
    experience_merged: str = Field(default="")


class SummarizerResponse(BaseResponse):
    experience_list: List[BaseExperience] = Field(default_factory=list)
    deleted_experience_ids: List[str] = Field(default_factory=list)


class VectorStoreResponse(BaseResponse):
    ...

class AgentResponse(BaseResponse):
    answer: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)
