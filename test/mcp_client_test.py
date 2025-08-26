from fastmcp import Client
from mcp.types import CallToolResult


async def main():
    async with Client("http://0.0.0.0:8002/sse/") as client:
        tools = await client.list_tools()
        for tool in tools:
            print(tool.model_dump_json())

        workspace_id = "default"

        result: CallToolResult = await client.call_tool("retrieve_task_memory_simple",
                                                        arguments={
                                                            "query": "茅台怎么样？",
                                                            "workspace_id": workspace_id,
                                                        })
        print(result.content)

        trajectories = [
            {
                "task_id": "t1",
                "messages": [
                    {"role": "user", "content": "今天天气不错"}
                ],
                "score": 0.9,
            }
        ]


        result: CallToolResult = await client.call_tool("summary_task_memory_simple",
                                                        arguments={
                                                            "trajectories": trajectories,
                                                            "workspace_id": workspace_id,
                                                        })
        print(result.content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
