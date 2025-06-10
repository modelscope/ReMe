import datetime
from typing import List
from uuid import uuid4

from pydantic import BaseModel, Field

from experiencemaker.schema.vector_store_node import VectorStoreNode


class ExperienceFunctionArg(BaseModel):
    arg_name: str = Field(default=..., description="argument name")
    arg_type: str = Field(default=..., description="argument type, like: 'str', 'int', 'bool'")
    required: bool = Field(default=True, description="whether the argument is required")


class ExperienceFunction(BaseModel):
    func_code: str = Field(default=..., description="function code")
    func_name: str = Field(default=..., description="function name")
    func_args: List[ExperienceFunctionArg] = Field(default_factory=list, description="function arguments")


class Experience(BaseModel):
    experience_id: str = Field(default_factory=lambda: uuid4().hex, description="experience unique id")
    experience_workspace_id: str = Field(default="", description="unique workspace id")
    experience_role: str = Field(default="", description="experience role")
    experience_desc: str = Field(default="", description="use condition/purpose. It will be used in vector matching")
    experience_content: str | bytes = Field(default="", description="content of the experience")
    experience_function: ExperienceFunction | None = Field(default=None, description="experience function(optional)")
    experience_score: float = Field(default=0.0, description="score of the experience")
    experience_created_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    experience_modified_time: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    metadata: dict = Field(default_factory=dict, description="additional metadata")

    def to_vector_store_node(self) -> VectorStoreNode:
        metadata: dict = {
            "experience_role": self.experience_role,
            "experience_content": self.experience_content,
            "experience_function": self.experience_function.model_dump(),
            "experience_score": self.experience_score,
            "experience_created_time": self.experience_created_time,
            "experience_modified_time": self.experience_modified_time,
            "metadata": self.metadata,
        }
        return VectorStoreNode(
            unique_id=self.experience_id,
            workspace_id=self.experience_workspace_id,
            content=self.experience_desc,
            metadata=metadata)

    @classmethod
    def from_vector_store_node(cls, node: VectorStoreNode) -> "Experience":
        return cls(
            experience_id=node.unique_id,
            experience_workspace_id=node.workspace_id,
            experience_role=node.metadata.get("experience_role", ""),
            experience_desc=node.content,
            experience_content=node.metadata.get("experience_content", ""),
            experience_function=node.metadata.get("experience_function", None),
            experience_score=node.metadata.get("experience_score", 0.0),
            experience_created_time=node.metadata.get("experience_created_time", ""),
            experience_modified_time=node.metadata.get("experience_modified_time", ""),
            metadata=node.metadata.get("metadata", {}))


if __name__ == "__main__":
    e1 = Experience(
        experience_workspace_id="w_1024",
        experience_role="qwen3",
        experience_desc="test desc",
        experience_content="test content",
        experience_function=ExperienceFunction(
            func_code="def a():\n    return",
            func_name="a",
            func_args=[ExperienceFunctionArg(arg_name="x", arg_type="str", required=True)]
        ),
        experience_score=0.99,
        metadata={"haha": 1}
    )
    print(e1.model_dump_json(indent=2))
    v1 = e1.to_vector_store_node()
    print(v1.model_dump_json(indent=2))
    e2 = Experience.from_vector_store_node(v1)
    print(e2.model_dump_json(indent=2))
