from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from v1.schema.message import Message, Trajectory


class BaseRequest(BaseModel, ABC):
    metadata: dict = Field(default_factory=dict)
    workspace_id: str = Field(default="")


class RetrieverRequest(BaseRequest):
    query: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)
    top_k: int = Field(default=3)


class SummarizerRequest(BaseRequest):
    traj_list: List[Trajectory] = Field(default_factory=list)


class VectorStoreRequest(BaseModel):
    action: str = Field(default="")
    params: dict = Field(default_factory=dict)


class AgentRequest(BaseModel):
    query: str = Field(default="")
