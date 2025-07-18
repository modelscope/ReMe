from typing import List

from pydantic import Field, BaseModel

from experiencemaker.schema.message import Message
from experiencemaker.tool.base_tool import BaseTool


class ReactContext(BaseModel):
    current_step: int = Field(default=-1)
    max_steps: int = Field(default=-1)
    query: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)
    has_terminate_tool: bool = Field(default=False)
    tools: List[BaseTool] = Field(default_factory=list)
    now_time: str = Field(default="")
    metadata: dict = Field(default_factory=dict)

    @property
    def tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]
