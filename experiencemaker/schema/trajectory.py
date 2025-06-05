import datetime
import json
from typing import List, Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from experiencemaker.enumeration.role import Role


class ToolCall(BaseModel):
    index: int = Field(default=...)
    id: str = Field(default="")
    name: str = Field(default="")
    arguments: str = Field(default="")
    type: str = Field(default="function")
    result: Any = Field(default=None, exclude=True)

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
    def argument_dict(self):
        return json.loads(self.arguments)

    @property
    def simple_dict(self):
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
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f",
        ),
    )
    metadata: dict = Field(default_factory=dict)

    @property
    def simple_dict(self) -> dict:
        result = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.tool_calls:
            result["tool_calls"] = [x.simple_dict for x in self.tool_calls]
        return result


class ActionMessage(Message):
    role: Role = Field(default=Role.ASSISTANT)


class StateMessage(Message):
    role: Role = Field(default=Role.TOOL)
    tool_call_id: str = Field(default="")

    @property
    def simple_dict(self) -> dict:
        result = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result

    @property
    def simple_list(self) -> list:
        return [{
            "role": self.role.value,
            "content": str(x.result),
            "tool_call_id": x.id,
        } for x in self.tool_calls]


class ContextMessage(Message):
    role: Role = Field(default=Role.CONTEXT_ASSISTANT)


class SummaryMessage(Message):
    role: Role = Field(default=Role.SUMMARY_ASSISTANT)


class Sample(BaseModel):
    steps: List[Message] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Trajectory(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    steps: List[Message] = Field(default_factory=list)

    done: bool = Field(default=False)
    query: str = Field(default="")
    answer: Any = Field(default=None)
    metadata: dict = Field(default_factory=dict)

    def add_step(self, step: Message):
        self.steps.append(step)

    def reset(self):
        self.steps.clear()
        self.done = False
        self.query = ""
        self.answer = ""
        self.metadata.clear()
