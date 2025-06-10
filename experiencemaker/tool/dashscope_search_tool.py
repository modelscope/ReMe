import os
from typing import Literal

import dashscope
from dashscope.api_entities.dashscope_response import Message
from loguru import logger
from pydantic import Field

from experiencemaker.tool.base_tool import BaseTool


class DashscopeSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Use search keywords to retrieve relevant information from the internet. " \
                       "If there are multiple search keywords, please use each keyword separately to call this tool."
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "search keyword",
            }
        },
        "required": ["query"]
    }

    model_name: Literal["qwen-plus-2025-04-28", "qwq-plus-latest", "qwen-max-2025-01-25"] = \
        Field(default="qwen-plus-2025-04-28")
    api_key: str = Field(default_factory=lambda: os.environ["DASHSCOPE_API_KEY"])
    stream_print: bool = Field(default=False)
    temperature: float = Field(default=0.0000001)
    use_role_prompt: bool = Field(default=True)
    role_prompt: str = """
# user's question
{question}

# task
Extract the original content related to the user's question directly from the context, maintain accuracy, and avoid excessive processing.    """.strip()
    return_only_content: bool = Field(default=True)

    def parse_reasoning_response(self, response, result: dict):
        is_answering = False
        is_first_chunk = True

        for chunk in response:
            if is_first_chunk:
                result["search_results"] = chunk.output.search_info["search_results"]

                if self.stream_print:
                    print("=" * 20 + "search result" + "=" * 20)
                    for web in result["search_results"]:
                        print(f"[{web['index']}]: [{web['title']}]({web['url']})")
                    print("=" * 20 + "thinking process" + "=" * 20)
                result["reasoning_content"] += chunk.output.choices[0].message.reasoning_content

                if self.stream_print:
                    print(chunk.output.choices[0].message.reasoning_content, end="", flush=True)
                is_first_chunk = False

            else:
                if chunk.output.choices[0].message.content == "" \
                        and chunk.output.choices[0].message.reasoning_content == "":
                    pass

                else:
                    if chunk.output.choices[0].message.reasoning_content != "" and \
                            chunk.output.choices[0].message.content == "":

                        if self.stream_print:
                            print(chunk.output.choices[0].message.reasoning_content, end="", flush=True)
                        result["reasoning_content"] += chunk.output.choices[0].message.reasoning_content

                    elif chunk.output.choices[0].message.content != "":
                        if not is_answering:
                            if self.stream_print:
                                print("\n" + "=" * 20 + "complete answer" + "=" * 20)
                            is_answering = True

                        if self.stream_print:
                            print(chunk.output.choices[0].message.content, end="", flush=True)
                        result["answer_content"] += chunk.output.choices[0].message.content

    def parse_response(self, response, result: dict):
        is_first_chunk = True

        for chunk in response:
            if is_first_chunk:
                result["search_results"] = chunk.output.search_info["search_results"]

                if self.stream_print:
                    print("=" * 20 + "search result" + "=" * 20)
                    for web in result["search_results"]:
                        print(f"[{web['index']}]: [{web['title']}]({web['url']})")
                    print("\n" + "=" * 20 + "complete answer" + "=" * 20)
                is_first_chunk = False

            else:
                if chunk.output.choices[0].message.content == "":
                    pass

                else:
                    if chunk.output.choices[0].message.content != "":
                        if self.stream_print:
                            print(chunk.output.choices[0].message.content, end="", flush=True)
                        result["answer_content"] += chunk.output.choices[0].message.content

    def execute(self, query: str = "", **kwargs):
        result = {
            "search_results": [],
            "reasoning_content": "",
            "answer_content": ""
        }
        user_query = self.role_prompt.format(question=query) if self.use_role_prompt else query
        messages = [Message(role="user", content=user_query)]

        response = dashscope.Generation.call(
            api_key=self.api_key,
            model=self.model_name,
            messages=messages,
            enable_thinking=True,
            enable_search=True,
            search_options={
                "forced_search": True,
                "enable_source": True,
                "enable_citation": False,
                "search_strategy": "pro"
            },
            stream=True,
            incremental_output=True,
            result_format="message",
        )

        if self.model_name != "qwen-max-2025-01-25":
            self.parse_reasoning_response(response, result)
        else:
            self.parse_response(response, result)

        if self.return_only_content:
            return result["answer_content"]
        else:
            return result

def main():
    from experiencemaker.utils.util_function import load_env_keys
    load_env_keys()
    query = "What is artificial intelligence?"

    tool = DashscopeSearchTool(stream_print=True)
    logger.info(tool.execute(query=query))

    tool = DashscopeSearchTool(stream_print=False)
    logger.info(tool.execute(query=query))

    tool = DashscopeSearchTool(stream_print=True, model_name="qwen-max-2025-01-25")
    logger.info(tool.execute(query=query))


if __name__ == '__main__':
    main()
