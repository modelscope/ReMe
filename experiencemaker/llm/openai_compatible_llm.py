import os
from typing import List

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from openai.types import CompletionUsage
from pydantic import Field, PrivateAttr, model_validator

from experiencemaker.enumeration.chunk_enum import ChunkEnum
from experiencemaker.enumeration.role import Role
from experiencemaker.llm import LLM_REGISTRY
from experiencemaker.llm.base_llm import BaseLLM
from experiencemaker.schema.message import Message, ToolCall
from experiencemaker.tool.base_tool import BaseTool


@LLM_REGISTRY.register("openai_compatible")
class OpenAICompatibleBaseLLM(BaseLLM):
    """
    OpenAI-compatible LLM implementation supporting streaming and tool calls.
    
    This class implements the BaseLLM interface for OpenAI-compatible APIs,
    including support for:
    - Streaming responses with different chunk types (thinking, answer, tools)
    - Tool calling with parallel execution
    - Reasoning/thinking content from supported models
    - Robust error handling and retries
    """
    
    # API configuration
    api_key: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY"), description="API key for authentication")
    base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL"), description="Base URL for the API endpoint")
    _client: OpenAI = PrivateAttr(description="OpenAI client instance (private)")

    @model_validator(mode="after")
    def init_client(self):
        """
        Initialize the OpenAI client after model validation.
        
        This validator runs after all field validation is complete,
        ensuring we have valid API credentials before creating the client.
        
        Returns:
            Self for method chaining
        """
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self

    def stream_chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        """
        Stream chat completions from OpenAI-compatible API.
        
        This method handles streaming responses and categorizes chunks into different types:
        - THINK: Reasoning/thinking content from the model
        - ANSWER: Regular response content
        - TOOL: Tool calls that need to be executed
        - USAGE: Token usage statistics
        - ERROR: Error information
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters
            
        Yields:
            Tuple of (chunk_content, ChunkEnum) for each streaming piece
        """
        for i in range(self.max_retries):
            try:
                # Create streaming completion request
                completion = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[x.simple_dump() for x in messages],
                    seed=self.seed,
                    top_p=self.top_p,
                    stream=True,
                    stream_options=self.stream_options,
                    temperature=self.temperature,
                    extra_body={"enable_thinking": self.enable_thinking},  # Enable reasoning mode
                    tools=[x.simple_dump() for x in tools] if tools else None,
                    tool_choice=self.tool_choice,
                    parallel_tool_calls=self.parallel_tool_calls)

                # Initialize tool call tracking
                ret_tools = []  # Accumulate tool calls across chunks
                is_answering = False  # Track when model starts answering

                # Process each chunk in the streaming response
                for chunk in completion:
                    # Handle chunks without choices (usually usage info)
                    if not chunk.choices:
                        yield chunk.usage, ChunkEnum.USAGE

                    else:
                        delta = chunk.choices[0].delta
                        
                        # Handle reasoning/thinking content (model's internal thoughts)
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                            yield delta.reasoning_content, ChunkEnum.THINK

                        else:
                            # Mark transition from thinking to answering
                            if not is_answering:
                                is_answering = True

                            # Handle regular response content
                            if delta.content is not None:
                                yield delta.content, ChunkEnum.ANSWER

                            # Handle tool calls (function calling)
                            if delta.tool_calls is not None:
                                for tool_call in delta.tool_calls:
                                    index = tool_call.index

                                    # Ensure we have enough tool call slots
                                    while len(ret_tools) <= index:
                                        ret_tools.append(ToolCall(index=index))

                                    # Accumulate tool call information across chunks
                                    if tool_call.id:
                                        ret_tools[index].id += tool_call.id

                                    if tool_call.function and tool_call.function.name:
                                        ret_tools[index].name += tool_call.function.name

                                    if tool_call.function and tool_call.function.arguments:
                                        ret_tools[index].arguments += tool_call.function.arguments

                # Yield completed tool calls after streaming finishes
                if ret_tools:
                    tool_dict = {x.name: x for x in tools} if tools else {}
                    for tool in ret_tools:
                        # Only yield tool calls that correspond to available tools
                        if tool.name not in tool_dict:
                            continue

                        yield tool, ChunkEnum.TOOL

                return  # Success - exit retry loop

            except Exception as e:
                logger.exception(f"stream chat with model={self.model_name} encounter error with e={e.args}")
                
                # Handle retry logic
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e
                else:
                    yield e.args, ChunkEnum.ERROR

    def _chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> Message:
        """
        Perform a complete chat completion by aggregating streaming chunks.
        
        This method consumes the entire streaming response and combines all
        chunks into a single Message object. It separates reasoning content,
        regular answer content, and tool calls.
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters
            
        Returns:
            Complete Message with all content aggregated
        """
        # Initialize content accumulators
        reasoning_content = ""  # Model's internal reasoning
        answer_content = ""     # Final response content
        tool_calls = []         # List of tool calls to execute

        # Consume streaming response and aggregate chunks by type
        for chunk, chunk_enum in self.stream_chat(messages, tools, **kwargs):
            if chunk_enum is ChunkEnum.THINK:
                reasoning_content += chunk

            elif chunk_enum is ChunkEnum.ANSWER:
                answer_content += chunk

            elif chunk_enum is ChunkEnum.TOOL:
                tool_calls.append(chunk)
            
            # Note: USAGE and ERROR chunks are ignored in non-streaming mode

        # Construct complete response message
        return Message(role=Role.ASSISTANT,
                       reasoning_content=reasoning_content,
                       content=answer_content,
                       tool_calls=tool_calls)

    def stream_print(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        """
        Stream chat completions with formatted console output.
        
        This method provides a real-time view of the model's response,
        with different formatting for different types of content:
        - Thinking content is wrapped in <think></think> tags
        - Answer content is printed directly
        - Tool calls are formatted as JSON
        - Usage statistics and errors are clearly marked
        
        Args:
            messages: List of conversation messages
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters
        """
        # Track which sections we've entered for proper formatting
        enter_think = False   # Whether we've started printing thinking content
        enter_answer = False  # Whether we've started printing answer content
        
        # Process each streaming chunk with appropriate formatting
        for chunk, chunk_enum in self.stream_chat(messages, tools, **kwargs):
            if chunk_enum is ChunkEnum.USAGE:
                # Display token usage statistics
                if isinstance(chunk, CompletionUsage):
                    print(f"\n<usage>{chunk.model_dump_json(indent=2)}</usage>")
                else:
                    print(f"\n<usage>{chunk}</usage>")

            elif chunk_enum is ChunkEnum.THINK:
                # Format thinking/reasoning content
                if not enter_think:
                    enter_think = True
                    print("<think>\n", end="")
                print(chunk, end="")

            elif chunk_enum is ChunkEnum.ANSWER:
                # Format regular answer content
                if not enter_answer:
                    enter_answer = True
                    # Close thinking section if we were in it
                    if enter_think:
                        print("\n</think>")
                print(chunk, end="")

            elif chunk_enum is ChunkEnum.TOOL:
                # Format tool calls as structured JSON
                assert isinstance(chunk, ToolCall)
                print(f"\n<tool>{chunk.model_dump_json(indent=2)}</tool>", end="")

            elif chunk_enum is ChunkEnum.ERROR:
                # Display error information
                print(f"\n<error>{chunk}</error>", end="")


def main():
    """
    Demo function to test the OpenAI-compatible LLM implementation.
    
    This function demonstrates:
    1. Basic chat without tools
    2. Chat with tool usage (search and code tools)
    3. Real-time streaming output formatting
    """
    from experiencemaker.tool.dashscope_search_tool import DashscopeSearchTool
    from experiencemaker.tool.code_tool import CodeTool
    from experiencemaker.enumeration.role import Role

    # Load environment variables for API credentials
    load_dotenv()
    
    # Initialize the LLM with a specific model
    model_name = "qwen-max-2025-01-25"
    llm = OpenAICompatibleBaseLLM(model_name=model_name)
    
    # Set up available tools
    tools: List[BaseTool] = [DashscopeSearchTool(), CodeTool()]

    # Test 1: Simple greeting without tools
    print("=== Test 1: Simple Chat ===")
    llm.stream_print([Message(role=Role.USER, content="hello")], [])
    
    print("\n" + "=" * 20)
    
    # Test 2: Complex query that might use tools
    print("\n=== Test 2: Chat with Tools ===")
    llm.stream_print([Message(role=Role.USER, content="What's the weather like in Beijing today?")], tools)


if __name__ == "__main__":
    main()
    # Launch with: python -m experiencemaker.llm.openai_compatible_llm
