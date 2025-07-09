from typing import List

from pydantic import BaseModel, Field

from v1.schema.message import Message, Trajectory


class BaseRequest(BaseModel):
    workspace_id: str = Field(default=...)
    config: dict = Field(default_factory=dict)
    metadata: dict | None = Field(default=None)


class RetrieverRequest(BaseRequest):
    query: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)


class SummarizerRequest(BaseRequest):
    traj_list: List[Trajectory] = Field(default_factory=list)


class VectorStoreRequest(BaseRequest):
    action: str = Field(default="")


class AgentRequest(BaseRequest):
    query: str = Field(default="")
