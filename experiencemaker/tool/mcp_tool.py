import asyncio
from typing import List

from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import Field, model_validator

from experiencemaker.tool import TOOL_REGISTRY
from experiencemaker.tool.base_tool import BaseTool


@TOOL_REGISTRY.register()
class MCPTool(BaseTool):
    server_url: str = Field(..., description="MCP server URL")
    tool_name_list: List[str] = Field(default_factory=list)
    cache_tools: dict = Field(default_factory=dict, alias="cache_tools")

    @model_validator(mode="after")
    def refresh_tools(self):
        self.refresh()
        return self

    async def _get_tools(self):
        async with sse_client(url=self.server_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                tools = await session.list_tools()
        return tools

    def refresh(self):
        self.tool_name_list.clear()
        self.cache_tools.clear()

        if "sse" in self.server_url:
            original_tool_list = asyncio.run(self._get_tools())
            for tool in original_tool_list.tools:
                self.cache_tools[tool.name] = tool
                self.tool_name_list.append(tool.name)
        else:
            raise NotImplementedError("Non-SSE refresh not implemented yet")

    @property
    def input_schema(self) -> dict:
        return {x: self.cache_tools[x].inputSchema for x in self.cache_tools}

    @property
    def output_schema(self) -> dict:
        raise NotImplementedError("Output schema not implemented yet")

    def get_tool_description(self, tool_name: str, schema: bool = False) -> str:
        if tool_name not in self.cache_tools:
            raise RuntimeError(f"Tool {tool_name} not found")

        tool = self.cache_tools.get(tool_name)
        description = f"tool={tool_name} description={tool.description}\n"
        if schema:
            description += f"input_schema={self.input_schema[tool_name]}\n" \
                           f"output_schema={self.output_schema[tool_name]}\n"
        return description.strip()

    async def async_execute(self, tool_name: str, **kwargs):
        if "sse" in self.server_url:
            async with sse_client(url=self.server_url) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    results = await session.call_tool(tool_name, kwargs)
            return results.content[0].text, results.isError

        else:
            raise NotImplementedError("Non-SSE execute not implemented yet")

    def _execute(self, **kwargs):
        return asyncio.run(self.async_execute(**kwargs))

    def get_cache_id(self, **kwargs) -> str:
        # Implement a method to generate a unique cache ID based on the input
        return f"{kwargs.get('tool_name')}_{hash(frozenset(kwargs.get('args', {}).items()))}"
