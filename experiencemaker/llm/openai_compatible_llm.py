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
    api_key: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY"), description="api key")
    base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL"), description="base url")
    _client: OpenAI = PrivateAttr()

    @model_validator(mode="after")
    def init_client(self):
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self

    def stream_chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        for i in range(self.max_retries):
            try:
                completion = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[x.simple_dump() for x in messages],
                    seed=self.seed,
                    top_p=self.top_p,
                    stream=True,
                    stream_options=self.stream_options,
                    temperature=self.temperature,
                    extra_body={"enable_thinking": self.enable_thinking},
                    tools=[x.simple_dump() for x in tools] if tools else None,
                    tool_choice=self.tool_choice,
                    parallel_tool_calls=self.parallel_tool_calls)

                ret_tools = []
                is_answering = False

                for chunk in completion:
                    if not chunk.choices:
                        yield chunk.usage, ChunkEnum.USAGE

                    else:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                            yield delta.reasoning_content, ChunkEnum.THINK

                        else:
                            if not is_answering:
                                is_answering = True

                            if delta.content is not None:
                                yield delta.content, ChunkEnum.ANSWER

                            if delta.tool_calls is not None:
                                for tool_call in delta.tool_calls:
                                    index = tool_call.index

                                    while len(ret_tools) <= index:
                                        ret_tools.append(ToolCall(index=index))

                                    if tool_call.id:
                                        ret_tools[index].id += tool_call.id

                                    if tool_call.function and tool_call.function.name:
                                        ret_tools[index].name += tool_call.function.name

                                    if tool_call.function and tool_call.function.arguments:
                                        ret_tools[index].arguments += tool_call.function.arguments

                if ret_tools:
                    tool_dict = {x.name: x for x in tools}
                    for tool in ret_tools:
                        if tool.name not in tool_dict:
                            continue

                        yield tool, ChunkEnum.TOOL

                return

            except  Exception as e:
                logger.exception(f"stream chat with model={self.model_name} encounter error with e={e.args}")
                if i == self.max_retries - 1 and self.raise_exception:
                    raise e
                else:
                    yield e.args, ChunkEnum.ERROR

    def _chat(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs) -> Message:
        reasoning_content = ""
        answer_content = ""
        tool_calls = []

        for chunk, chunk_enum in self.stream_chat(messages, tools, **kwargs):
            if chunk_enum is ChunkEnum.THINK:
                reasoning_content += chunk

            elif chunk_enum is ChunkEnum.ANSWER:
                answer_content += chunk

            elif chunk_enum is ChunkEnum.TOOL:
                tool_calls.append(chunk)

        return Message(role=Role.ASSISTANT,
                       reasoning_content=reasoning_content,
                       content=answer_content,
                       tool_calls=tool_calls)

    def stream_print(self, messages: List[Message], tools: List[BaseTool] = None, **kwargs):
        enter_think = False
        enter_answer = False
        for chunk, chunk_enum in self.stream_chat(messages, tools, **kwargs):
            if chunk_enum is ChunkEnum.USAGE:
                if isinstance(chunk, CompletionUsage):
                    print(f"\n<usage>{chunk.model_dump_json(indent=2)}</usage>")
                else:
                    print(f"\n<usage>{chunk}</usage>")

            elif chunk_enum is ChunkEnum.THINK:
                if not enter_think:
                    enter_think = True
                    print("<think>\n", end="")
                print(chunk, end="")

            elif chunk_enum is ChunkEnum.ANSWER:
                if not enter_answer:
                    enter_answer = True
                    if enter_think:
                        print("\n</think>")
                print(chunk, end="")

            elif chunk_enum is ChunkEnum.TOOL:
                assert isinstance(chunk, ToolCall)
                print(f"\n<tool>{chunk.model_dump_json(indent=2)}</tool>", end="")

            elif chunk_enum is ChunkEnum.ERROR:
                print(f"\n<error>{chunk}</error>", end="")


def main():
    from experiencemaker.tool.dashscope_search_tool import DashscopeSearchTool
    from experiencemaker.tool.code_tool import CodeTool
    from experiencemaker.enumeration.role import Role

    load_dotenv()
    model_name = "qwen-max-2025-01-25"
    llm = OpenAICompatibleBaseLLM(model_name=model_name)
    tools: List[BaseTool] = [DashscopeSearchTool(), CodeTool()]

    llm.stream_print([Message(role=Role.USER, content="hello")], [])
    print("=" * 20)
    llm.stream_print([Message(role=Role.USER, content="What's the weather like in Beijing today?")], tools)


if __name__ == "__main__":
    main()
    # launch with: python -m experiencemaker.model.openai_compatible_llm
