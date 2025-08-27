import datetime
from abc import ABC
from typing import List
from uuid import uuid4

from flowllm.schema.vector_node import VectorNode
from pydantic import BaseModel, Field


class BaseMemory(BaseModel, ABC):
    workspace_id: str = Field(default="")
    memory_id: str = Field(default_factory=lambda: uuid4().hex)
    memory_type: str = Field(default=...)

    when_to_use: str = Field(default="")
    content: str | bytes = Field(default="")
    score: float | None = Field(default=None)

    created_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    modified_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    author: str = Field(default="")

    metadata: dict = Field(default_factory=dict)

    def update_modified_time(self):
        self.modified_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def update_metadata(self, new_metadata):
        self.metadata = new_metadata

    def to_vector_node(self) -> VectorNode:
        raise NotImplementedError

    @classmethod
    def from_vector_node(cls, node: VectorNode):
        raise NotImplementedError


class TaskMemory(BaseMemory):
    memory_type: str = Field(default="task")

    def to_vector_node(self) -> VectorNode:
        return VectorNode(unique_id=self.memory_id,
                          workspace_id=self.workspace_id,
                          content=self.when_to_use,
                          metadata={
                              "memory_type": self.memory_type,
                              "content": self.content,
                              "score": self.score,
                              "created_time": self.created_time,
                              "modified_time": self.modified_time,
                              "author": self.author,
                              "metadata": self.metadata,
                          })

    @classmethod
    def from_vector_node(cls, node: VectorNode) -> "TaskMemory":
        return cls(workspace_id=node.workspace_id,
                   memory_id=node.unique_id,
                   memory_type=node.metadata.get("memory_type"),
                   when_to_use=node.content,
                   content=node.metadata.get("content"),
                   score=node.metadata.get("score"),
                   created_time=node.metadata.get("created_time"),
                   modified_time=node.metadata.get("modified_time"),
                   author=node.metadata.get("author"),
                   metadata=node.metadata.get("metadata"))


class FunctionArg(BaseModel):
    arg_name: str = Field(default=...)
    arg_type: str = Field(default=...)
    required: bool = Field(default=True)


class Function(BaseModel):
    func_code: str = Field(default=..., description="function code")
    func_name: str = Field(default=..., description="function name")
    func_args: List[FunctionArg] = Field(default_factory=list)


class FuncMemory(BaseMemory):
    memory_type: str = Field(default="function")
    functions: List[Function] = Field(default_factory=list)


class PersonalMemory(BaseMemory):
    memory_type: str = Field(default="personal")
    target: str = Field(default="")


class PersonalTopicMemory(PersonalMemory):
    memory_type: str = Field(default="personal_topic")


def vector_node_to_memory(node: VectorNode) -> BaseMemory:
    memory_type = node.metadata.get("memory_type")
    if memory_type == "task":
        return TaskMemory.from_vector_node(node)

    elif memory_type == "function":
        return FuncMemory.from_vector_node(node)

    elif memory_type == "personal":
        return PersonalMemory.from_vector_node(node)

    elif memory_type == "personal_topic":
        return PersonalTopicMemory.from_vector_node(node)

    else:
        raise RuntimeError(f"memory_type={memory_type} not supported!")


def dict_to_memory(memory_dict: dict):
    memory_type = memory_dict.get("memory_type", "task")
    if memory_type == "task":
        return TaskMemory(**memory_dict)

    elif memory_type == "function":
        return FuncMemory(**memory_dict)

    elif memory_type == "personal":
        return PersonalMemory(**memory_dict)

    elif memory_type == "personal_topic":
        return PersonalTopicMemory(**memory_dict)

    else:
        raise RuntimeError(f"memory_type={memory_type} not supported!")


if __name__ == "__main__":
    e1 = TaskMemory(
        workspace_id="w_1024",
        memory_id="123",
        when_to_use="test case use",
        content="test content",
        score=0.99,
        metadata={})
    print(e1.model_dump_json(indent=2))
    v1 = e1.to_vector_node()
    print(v1.model_dump_json(indent=2))
    e2 = vector_node_to_memory(v1)
    print(e2.model_dump_json(indent=2))
