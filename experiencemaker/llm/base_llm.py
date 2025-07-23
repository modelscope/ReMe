import time
from abc import ABC
from typing import List, Literal, Callable

from loguru import logger
from pydantic import Field, BaseModel

from experiencemaker.schema.message import Message
from experiencemaker.tool.base_tool import BaseTool


class BaseLLM(BaseModel, ABC):
    model_name: str = Field(...)

    seed: int = Field(default=42)
    top_p: float | None = Field(default=None)
    # stream: bool = Field(default=True)
    stream_options: dict = Field(default={"include_usage": True})
    temperature: float = Field(default=0.0000001)
    presence_penalty: float | None = Field(default=None)
    enable_thinking: bool = Field(default=True, description="whether the current mode is the reasoning model, "
                                                            "or whether Qwen3's reasoning mode is currently enabled.")
    tool_choice: Literal["none", "auto", "required"] = Field(default="auto", description="tool choice")
    parallel_tool_calls: bool = Field(default=True)

    max_retries: int = Field(default=5, description="max retries")
    raise_exception: bool = Field(default=False, description="raise exception")

    def stream_chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        raise NotImplementedError

    def stream_print(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        raise NotImplementedError

    def _chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> Message:
        raise NotImplementedError

    def chat(self, messages: List[Message], tools: List[BaseTool] = None, callback_fn: Callable = None,
             default_value=None, **kwargs):
        for i in range(self.max_retries):
            try:
                message: Message = self._chat(messages, tools, **kwargs)
                if callback_fn:
                    return callback_fn(message)
                else:
                    return message

            except Exception as e:
                logger.exception(f"chat with model={self.model_name} encounter error with e={e.args}")
                time.sleep(1 + i)

                if i == self.max_retries - 1:
                    if self.raise_exception:
                        raise e
                    else:
                        return default_value

        return None
