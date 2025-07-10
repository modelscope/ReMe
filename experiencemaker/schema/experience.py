import datetime
from abc import ABC
from typing import List
from uuid import uuid4

from pydantic import BaseModel, Field

from experiencemaker.schema.vector_node import VectorNode


class ExperienceMeta(BaseModel):
    author: str = Field(default="")
    created_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    modified_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    extra_info: dict | None = Field(default=None)

    def update_modified_time(self):
        self.modified_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BaseExperienceNode(BaseModel, ABC):
    workspace_id: str = Field(default="")

    experience_id: str = Field(default_factory=lambda: uuid4().hex)
    experience_type: str = Field(default="text")

    when_to_use: str = Field(default="")
    content: str | bytes = Field(default="")
    score: float | None = Field(default=None)
    metadata: ExperienceMeta = Field(default_factory=ExperienceMeta)

    def to_vector_node(self) -> VectorNode:
        raise NotImplementedError

    @classmethod
    def from_vector_node(cls, node: VectorNode) -> "BaseExperienceNode":
        raise NotImplementedError


class TextExperienceNode(BaseExperienceNode):
    ...


class FunctionArg(BaseModel):
    arg_name: str = Field(default=...)
    arg_type: str = Field(default=...)
    required: bool = Field(default=True)


class Function(BaseModel):
    func_code: str = Field(default=..., description="function code")
    func_name: str = Field(default=..., description="function name")
    func_args: List[FunctionArg] = Field(default_factory=list)


class FuncExperienceNode(BaseExperienceNode):
    experience_type: str = Field(default="function")
    functions: List[Function] = Field(default_factory=list)


class PersonalExperienceNode(BaseExperienceNode):
    experience_type: str = Field(default="personal")
    person: str = Field(default="")
    topic: str = Field(default="")


class KnowledgeExperienceNode(BaseExperienceNode):
    experience_type: str = Field(default="knowledge")
    topic: str = Field(default="")
