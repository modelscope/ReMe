import asyncio
import datetime
import json

from flowllm.context import C
from flowllm.enumeration.role import Role
from flowllm.op.base_async_tool_op import BaseAsyncToolOp
from flowllm.schema.message import Message
from flowllm.schema.tool_call import ToolCall
from flowllm.utils.timer import Timer
from flowllm.utils.token_utils import TokenCounter
from loguru import logger

from reme_ai.agent.tools.mock_search_tools import SearchToolA, SearchToolB, SearchToolC
from reme_ai.schema.memory import ToolCallResult


@C.register_op()
class UseMockSearchOp(BaseAsyncToolOp):
    file_path: str = __file__

    def __init__(self, llm: str = "qwen3_30b_instruct", **kwargs):
        super().__init__(llm=llm, save_answer=True, **kwargs)

    def build_tool_call(self) -> ToolCall:
        return ToolCall(**{
            "description": "Intelligently selects and executes the most appropriate search tool based on query complexity. "
                           "Automatically tracks performance metrics and records tool usage for optimization.",
            "input_schema": {
                "query": {
                    "type": "string",
                    "description": "query",
                    "required": True
                }
            }
        })

    async def select_tool(self, query: str, tool_ops: list[BaseAsyncToolOp]) -> ToolCall | None:
        assistant_message = await self.llm.achat(messages=[Message(role=Role.USER, content=query)],
                                        tools=[x.tool_call for x in tool_ops])
        logger.info(f"assistant_message={assistant_message.model_dump_json()}")
        if assistant_message.tool_calls:
            return assistant_message.tool_calls[0]

        return None

    async def async_execute(self):
        query: str = self.input_dict["query"]
        logger.info(f"query={query}")

        tool_ops = [
            SearchToolA(),
            SearchToolB(),
            SearchToolC(),
        ]

        # Step 1: Select the appropriate tool using LLM
        tool_call = await self.select_tool(query, tool_ops)

        if tool_call is None:
            # No tool selected
            error_result = ToolCallResult(
                create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                tool_name="None",
                input={"query": query},
                output="No appropriate tool was selected for the query",
                token_cost=0,
                success=False,
                time_cost=0.0
            )
            self.set_result(error_result.model_dump_json())
            return

            # Step 2: Execute the selected tool
        selected_op = None
        for op in tool_ops:
            if op.tool_call.name == tool_call.name:
                selected_op = op
                break

        if selected_op is None:
            # Tool not found (should not happen)
            error_result = ToolCallResult(
                create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                tool_name=tool_call.name,
                input=tool_call.arguments,
                output=f"Tool {tool_call.name} not found in available tools",
                token_cost=0,
                success=False,
                time_cost=0.0
            )
            self.set_result(error_result.model_dump_json())
            return

        # Step 3: Execute the tool with timer
        timer = Timer("tool execute")
        with timer:
            await selected_op.async_call(query=query)
            selected_op_output = json.loads(selected_op.output)
            content = selected_op_output["content"]
            success = selected_op_output["success"]
            token_cost = TokenCounter().count(content)

        time_cost = timer.time_cost

        # Create ToolCallResult
        tool_call_result = ToolCallResult(
            create_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tool_name=tool_call.name,
            input={"query": query},
            output=content,
            token_cost=token_cost,
            success=success,
            time_cost=round(time_cost, 3)
        )

        self.set_result(tool_call_result.model_dump_json())


async def async_main():
    from flowllm.app import FlowLLMApp

    async with FlowLLMApp(load_default_config=True):
        test_queries = [
            "What is the capital of France?",
            "How does quantum computing work?",
            "Analyze the impact of artificial intelligence on global economy, employment, and society",
            "When was Python programming language created?",
            "Compare different types of renewable energy sources",  
        ]

        for query in test_queries:
            op = UseMockSearchOp()
            await op.async_call(query=query)
            print(op.output)


if __name__ == "__main__":
    asyncio.run(async_main())

