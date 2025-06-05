
import asyncio
from typing import List, Optional

from loguru import logger
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import Field

from experiencescope.tool.base_tool import BaseTool


class MCPTool(BaseTool):
    server_url: str = Field(..., description="MCP server URL")
    tool_name_list: List[str] = Field(default_factory=list)
    cache_tools: dict = Field(default_factory=dict, alias="cache_tools")
    cache_tools_info: Optional[dict] = Field(default=None, alias="cache_tools_info")

    class Config:
        underscore_attrs_are_private = True

    def __init__(self, **data):
        super().__init__(**data)
        self.refresh()

    def get_tool_name_list(self) -> List[str]:
        return self.tool_name_list

    def get_server_info(self):
        return self.cache_tools_info

    def refresh(self):
        self.cache_tools.clear()
        self.tool_name_list.clear()

        if "sse" in self.server_url:
            original_tool_list = asyncio.run(self._get_tools())
            self.cache_tools_info = original_tool_list.tools

            for tool in self.cache_tools_info:
                self.cache_tools[tool.name] = tool
                self.tool_name_list.append(tool.name)
        else:
            # TODO: Implement non-SSE refresh logic
            logger.warning("Non-SSE refresh not implemented yet")

    async def _get_tools(self):
        async with sse_client(url=self.server_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                tools = await session.list_tools()
        return tools

    def input_schema(self, tool_name: str) -> dict:
        return self.cache_tools.get(tool_name, {}).inputSchema

    def output_schema(self, tool_name: str) -> dict:
        # TODO: Implement output schema logic
        return {}

    def get_tool_description(self, tool_name: str, schema: bool = False) -> str:
        tool = self.cache_tools.get(tool_name)
        if not tool:
            return ""

        description = f'tool \'{tool_name}\' description is:'+ tool.description
        if schema:
            description += f"\nInput Schema: {self.input_schema(tool_name)}"
            description += f"\nOutput Schema: {self.output_schema(tool_name)}"
        return description

    async def _execute(self, **kwargs):
        tool_name = kwargs.get('tool_name')
        args = kwargs.get('args', {})

        if "sse" in self.server_url:
            async with sse_client(url=self.server_url) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    results = await session.call_tool(tool_name, args)
            return results.content[0].text, results.isError
        else:
            return "Failed to connect to the tool", False

    def execute(self, **kwargs):
        return asyncio.run(self._execute(**kwargs))

    def get_cache_id(self, **kwargs) -> str:
        # Implement a method to generate a unique cache ID based on the input
        return f"{kwargs.get('tool_name')}_{hash(frozenset(kwargs.get('args', {}).items()))}"

