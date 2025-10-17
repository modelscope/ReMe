import datetime
from abc import ABC
from typing import List
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel, Field

from experiencemaker.schema.vector_node import VectorNode


class ExperienceMeta(BaseModel):
    author: str = Field(default="")
    task_query: str = Field(default="")
    when_to_use: str = Field(default="")
    category: str = Field(default="")
    created_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    modified_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    extra_info: dict | None = Field(default=None)

    def update_modified_time(self):
        self.modified_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BaseExperience(BaseModel, ABC):
    workspace_id: str = Field(default="")

    experience_id: str = Field(default_factory=lambda: uuid4().hex)
    experience_type: str = Field(default="")

    when_to_use: str = Field(default="")
    content: str | bytes = Field(default="")
    score: float | None = Field(default=None)
    task_query: str = Field(default="")
    freq: int = Field(default=0)
    utility: int = Field(default=0)
    metadata: ExperienceMeta = Field(default_factory=ExperienceMeta)

    def to_vector_node(self) -> VectorNode:
        raise NotImplementedError

    @classmethod
    def from_vector_node(cls, node: VectorNode):
        raise NotImplementedError

    def update_score(self, score):
        self.score = score


class TextExperience(BaseExperience):
    experience_type: str = Field(default="text")

    def to_vector_node(self) -> VectorNode:
        return VectorNode(unique_id=self.experience_id,
                          workspace_id=self.workspace_id,
                        #   content=",".join(self.metadata.extra_info["tags"]),
                          content=self.when_to_use,
                        #   content=self.task_query,
                        #   content=self.metadata.extra_info["generalized_query"],
                          metadata={
                              "experience_type": self.experience_type,
                              "experience_content": self.content,
                              "score": self.score,
                              "when_to_use": self.when_to_use, # new added
                              "task_query": self.task_query,
                              "metadata": self.metadata.model_dump(),
                          })

    @classmethod
    def from_vector_node(cls, node: VectorNode):
        return cls(workspace_id=node.workspace_id,
                   experience_id=node.unique_id,
                   experience_type=node.metadata.get("experience_type"),
                #    when_to_use=node.content,
                   when_to_use=node.metadata.get("when_to_use"),
                   task_query=node.metadata.get("task_query"),
                   content=node.metadata.get("experience_content"),
                   score=node.metadata.get("score"),
                   freq=node.freq,
                   utility=node.utility,
                   metadata=node.metadata.get("metadata"))


class FunctionArg(BaseModel):
    arg_name: str = Field(default=...)
    arg_type: str = Field(default=...)
    required: bool = Field(default=True)


class Function(BaseModel):
    func_code: str = Field(default=..., description="function code")
    func_name: str = Field(default=..., description="function name")
    func_args: List[FunctionArg] = Field(default_factory=list)


class FuncExperience(BaseExperience):
    experience_type: str = Field(default="function")
    functions: List[Function] = Field(default_factory=list)


class PersonalExperience(BaseExperience):
    experience_type: str = Field(default="personal")
    person: str = Field(default="")
    topic: str = Field(default="")


class KnowledgeExperience(BaseExperience):
    experience_type: str = Field(default="knowledge")
    topic: str = Field(default="")


def vector_node_to_experience(node: VectorNode) -> BaseExperience:
    experience_type = node.metadata.get("experience_type")
    if experience_type == "text":
        return TextExperience.from_vector_node(node)

    elif experience_type == "function":
        return FuncExperience.from_vector_node(node)

    elif experience_type == "personal":
        return PersonalExperience.from_vector_node(node)

    elif experience_type == "knowledge":
        return KnowledgeExperience.from_vector_node(node)

    else:
        logger.warning(f"experience type {experience_type} not supported")
        return TextExperience.from_vector_node(node)


def dict_to_experience(experience_dict: dict) -> BaseExperience:
    experience_type = experience_dict.get("experience_type", "text")
    if experience_type == "text":
        return TextExperience(**experience_dict)

    elif experience_type == "function":
        return FuncExperience(**experience_dict)

    elif experience_type == "personal":
        return PersonalExperience(**experience_dict)

    elif experience_type == "knowledge":
        return KnowledgeExperience(**experience_dict)

    else:
        logger.warning(f"experience type {experience_type} not supported")
        return TextExperience(**experience_dict)


if __name__ == "__main__":
    e1 = TextExperience(
        workspace_id="w_1024",
        experience_id="123",
        when_to_use="test case use",
        content="test content",
        score=0.99,
        metadata=ExperienceMeta(author="user"))
    print(e1.model_dump_json(indent=2))
    v1 = e1.to_vector_node()
    print(v1.model_dump_json(indent=2))
    e2 = vector_node_to_experience(v1)
    print(e2.model_dump_json(indent=2))
