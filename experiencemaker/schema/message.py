import json
from typing import List

from pydantic import BaseModel, Field, model_validator

from experiencemaker.enumeration.role import Role


class ToolCall(BaseModel):
    index: int = Field(default=0)
    id: str = Field(default="")
    name: str = Field(default="")
    arguments: str = Field(default="")
    type: str = Field(default="function")

    @model_validator(mode="before")  # noqa
    @classmethod
    def init_tool_call(cls, data: dict):
        tool_type = data.get("type", "")
        tool_type_dict = data.get(tool_type, {})

        for key in ["name", "arguments"]:
            if key not in data:
                data[key] = tool_type_dict.get(key, "")
        return data

    @property
    def argument_dict(self) -> dict:
        return json.loads(self.arguments)

    def simple_dump(self) -> dict:
        return {
            "id": self.id,
            self.type: {
                "arguments": self.arguments,
                "name": self.name
            },
            "type": self.type,
            "index": self.index,
        }

class Message(BaseModel):
    role: Role = Field(default=Role.USER)
    content: str | bytes = Field(default="")
    reasoning_content: str = Field(default="")
    tool_calls: List[ToolCall] = Field(default_factory=list)
    tool_call_id: str = Field(default="")
    metadata: dict = Field(default_factory=dict)

    def simple_dump(self, add_reason_when_empty: bool = True) -> dict:
        result: dict
        if self.content:
            result = {"role": self.role.value, "content": self.content}
        elif add_reason_when_empty and self.reasoning_content:
            result = {"role": self.role.value, "content": self.reasoning_content}
        else:
            result = {"role": self.role.value, "content": ""}

        if self.tool_calls:
            result["tool_calls"] = [x.simple_dump() for x in self.tool_calls]
        return result


class Trajectory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    score: float = Field(default=0.0)
    metadata: dict = Field(default_factory=dict)
