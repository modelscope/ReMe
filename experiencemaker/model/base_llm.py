from abc import ABC
from typing import List, Literal

from loguru import logger
from pydantic import Field, BaseModel

from experiencemaker.schema.trajectory import Message, ActionMessage
from experiencemaker.tool.base_tool import BaseTool
from experiencemaker.utils.registry import Registry


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

    max_retries: int = Field(default=3, description="max retries")
    raise_exception: bool = Field(default=True, description="raise exception")

    def stream_chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        """
        This method is designed to handle streaming chat functionality, allowing for interactive communication
        with the ability to use various tools. It is intended to be overridden by subclasses to implement
        specific streaming chat logic.

        Parameters:
        - messages: A list of Message objects, representing the message history or current messages in the chat.
        - tools: An optional list of BaseTool objects, representing the tools available for use during the chat.
        - **kwargs: Additional keyword arguments for future expansion or specific implementations.

        Raises:
        - NotImplementedError: This method raises a NotImplementedError to indicate that the functionality
          should be implemented by subclasses.
        """
        raise NotImplementedError

    def stream_print(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        """
        This method is intended to be overridden by subclasses to implement specific message streaming printing logic.
        The method raises a NotImplementedError, indicating that this is an abstract method that must be implemented by subclasses.

        Parameters:
        - messages: A list of Message objects, representing the messages to be printed.
        - tools: An optional list of BaseTool objects, representing auxiliary tools that may be needed during the printing process.
        - **kwargs: Additional keyword arguments, allowing for flexible handling of extra parameters.

        Raises:
        - NotImplementedError: Indicates that the method is abstract and needs to be implemented by a subclass.
        """
        raise NotImplementedError

    def _chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> ActionMessage:
        """
        Abstract method for processing chat messages and generating responses.

        This method is designed to be overridden by subclasses to implement specific chat logic.
        It receives a list of messages as input, along with optional tools, and is expected to return
        an ActionMessage object as a response. The method raises a NotImplementedError to enforce
        implementation by subclasses.

        Parameters:
        - messages: List[Message] - A list of Message objects representing the chat history or current messages.
        - tools: List[BaseTool] (optional) - A list of BaseTool objects representing the tools available for use during the chat. Defaults to None.
        - **kwargs: Additional keyword arguments for extensibility and backwards compatibility.

        Returns:
        - ActionMessage: The response generated based on the input messages, encapsulated in an ActionMessage object.
        """
        raise NotImplementedError

    def chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> ActionMessage | None:
        """
        Initiates a chat session with a model, allowing for the execution of tools.

        This function sends a series of messages to the model and expects to receive an execution response.
        It can handle exceptions during the chat process by retrying a set number of times.

        Parameters:
        - messages (List[Message]): A list of message objects, containing the conversation history.
        - tools (List[BaseTool], optional): A list of tool objects that can be used during the chat. Defaults to None.
        - **kwargs: Additional parameters that can be passed to the model.

        Returns:
        - ActionMessage: A response message containing the model's execution results.
        - None: Returns None if the maximum number of retries is reached and no successful response is obtained.
        """

        # Iterate according to the maximum number of retries set
        for i in range(self.max_retries):
            try:
                # Attempt to execute the chat logic
                return self._chat(messages, tools, **kwargs)

            except Exception as e:
                # Log exceptions during the chat process
                logger.exception(f"chat with model={self.model_name} encounter error with e={e.args}")

                # If the maximum number of retries is reached and raise_exception is set to True, then re-throw the exception
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e

        return None


LLM_REGISTRY = Registry[BaseLLM]("llm")
