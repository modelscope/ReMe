import asyncio
import json
from typing import Dict, Any

from flowllm.op.gallery.task_react_op import tools_schema_to_qwen_prompt
from flowllm.schema.tool_call import ToolCall
from loguru import logger

from flowllm.context import FlowContext, C
from flowllm.enumeration.role import Role
from flowllm.op.base_async_tool_op import BaseAsyncToolOp
from flowllm.schema.message import Message

from reme_ai.agent.tools.mock_search_tools import SearchToolA, SearchToolB, SearchToolC


@C.register_op()
class UseMockSearchOp(BaseAsyncToolOp):
    file_path: str = __file__

    def __init__(self, llm: str = "qwen3_30b_instruct", **kwargs):
        super().__init__(llm=llm, **kwargs)

    async def select_tool(self, query: str, tool_ops: list[BaseAsyncToolOp]) -> ToolCall | None:
        assistant_message = await self.llm.achat(messages=[Message(role=Role.USER, content=query)],
                                        tools=[x.tool_call for x in tool_ops])

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

        tool_result = await self.select_tool(query, tool_ops)
        if tool_result is None:
            ...
            return

        for op in tool_ops:
            op.tool_call.name == tool_result.name


async def async_main():
    """Test the UseMockSearchOp with different query types."""
    from flowllm.app import FlowLLMApp

    async with FlowLLMApp(load_default_config=True):
        # Test queries of different complexities
        test_queries = [
            "What is the capital of France?",  # Simple - should select SearchToolA
            "How does quantum computing work?",  # Medium - should select SearchToolB
            "Analyze the impact of artificial intelligence on global economy, employment, and society",  # Complex - should select SearchToolC
            "When was Python programming language created?",  # Simple
            "Compare different types of renewable energy sources",  # Complex
        ]

        op = UseMockSearchOp()

        for query in test_queries:
            print(f"\n{'=' * 100}")
            print(f"Query: {query}")
            print(f"{'=' * 100}")

            context = FlowContext(query=query)
            await op.async_call(context=context)
            
            result = json.loads(context.use_mock_search_result)
            print(f"\nSelected Tool: {result['selected_tool']}")
            print(f"Reasoning: {result['reasoning']}")
            print(f"Complexity: {result['complexity']}")
            print(f"Success: {result['success']}")
            print(f"\nContent:\n{result['content']}")
            print(f"\n{'=' * 100}\n")


if __name__ == "__main__":
    asyncio.run(async_main())

