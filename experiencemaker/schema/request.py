from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.message import Message, Trajectory


class BaseRequest(BaseModel):
    workspace_id: str = Field(default="default")
    config: dict = Field(default_factory=dict)


class RetrieverRequest(BaseRequest):
    query: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)
    top_k: int = Field(default=1)


class SummarizerRequest(BaseRequest):
    traj_list: List[Trajectory] = Field(default_factory=list)


class VectorStoreRequest(BaseRequest):
    action: str = Field(default="")
    src_workspace_id: str = Field(default="")
    path: str = Field(default="")


class AgentRequest(BaseRequest):
    query: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)

