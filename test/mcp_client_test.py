from fastmcp import Client
from mcp.types import CallToolResult


async def main():
    async with Client("http://0.0.0.0:8002/sse/") as client:
        tools = await client.list_tools()
        for tool in tools:
            print(tool.model_dump_json())

        result: CallToolResult = await client.call_tool("retrieve_task_memory",
                                                        arguments={
                                                            "query": "茅台怎么样？",
                                                            "workspace_id": "default",
                                                            "top_k": 1,
                                                        })
        print(result.content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
