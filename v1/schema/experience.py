import datetime
from abc import ABC
from typing import List
from uuid import uuid4

from pydantic import BaseModel, Field

from v1.schema.vector_store_node import VectorStoreNode


class ExperienceMeta(BaseModel):
    author: str = Field(default="")
    created_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    modified_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    extra_info: dict | None = Field(default=None)


class BaseExperienceNode(BaseModel, ABC):
    experience_id: str = Field(default_factory=lambda: uuid4().hex)
    experience_type: str = Field(default="text")
    workspace_id: str = Field(default="")
    experience_meta: ExperienceMeta | None = Field(default=None)

    def to_vector_store_node(self) -> VectorStoreNode:
        ...

    @classmethod
    def from_vector_store_node(cls, node: VectorStoreNode) -> "TextExperienceNode":
        ...


class TextExperienceNode(BaseExperienceNode):
    experience_type: str = Field(default="text")
    when_to_use: str = Field(default="")
    content: str | bytes = Field(default="")
    score: float | None = Field(default=None)


class FunctionArg(BaseModel):
    arg_name: str = Field(default=...)
    arg_type: str = Field(default=...)
    required: bool = Field(default=True)


class Function(BaseModel):
    func_code: str = Field(default=..., description="function code")
    func_name: str = Field(default=..., description="function name")
    func_args: List[FunctionArg] = Field(default_factory=list)


class FuncExperienceNode(BaseExperienceNode):
    """
    TODO
    """
    experience_type: str = Field(default="func")
    functions: List[Function] = Field(default_factory=list)


class PersonalExperienceNode(BaseExperienceNode):
    """
    TODO: memory node from MemoryScope
    """
    experience_type: str = Field(default="personal")
    person: str = Field(default="")
    topic: str = Field(default="")
    content: str | bytes = Field(default="")


class KnowledgeExperienceNode(BaseExperienceNode):
    """
    TODO
    """
    experience_type: str = Field(default="knowledge")
    topic: str = Field(default="")
    content: str | bytes = Field(default="")
    score: float | None = Field(default=None)
