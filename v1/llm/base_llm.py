import time
from abc import ABC
from typing import List, Literal

from loguru import logger, Message
from pydantic import Field, BaseModel

from v1.tool.base_tool import BaseTool


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
    raise_exception: bool = Field(default=True, description="raise exception")

    def stream_chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        raise NotImplementedError

    def stream_print(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        raise NotImplementedError

    def _chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> ActionMessage:
        raise NotImplementedError

    def chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> ActionMessage | None:
        for i in range(self.max_retries):
            try:
                # Attempt to execute the chat logic
                return self._chat(messages, tools, **kwargs)

            except Exception as e:
                # Log exceptions during the chat process
                logger.exception(f"chat with model={self.model_name} encounter error with e={e.args}")
                time.sleep(1 + i)

                # If the maximum number of retries is reached and raise_exception is set to True, then re-throw the exception
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e

        return None
