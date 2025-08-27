import asyncio

import aiohttp


async def main():
    base_url = "http://0.0.0.0:8002"

    async with aiohttp.ClientSession() as session:
        # 获取工具列表
        print("获取工具列表...")
        async with session.get(f"{base_url}/list") as response:
            if response.status == 200:
                tools = await response.json()
                print("可用工具:")
                for tool in tools:
                    print(tool)
            else:
                print(f"获取工具列表失败: {response.status}")
                return

        workspace_id = "default1"

        trajectories = [
            {
                "task_id": "t1",
                "messages": [
                    {"role": "user", "content": "搜索可以使用websearch工具"}
                ],
                "score": 0.9,
            }
        ]

        async with session.post(
                f"{base_url}/summary_task_memory_simple",
                json={
                    "trajectories": trajectories,
                    "workspace_id": workspace_id,
                },
                headers={"Content-Type": "application/json"}
        ) as response:
            result = await response.json()
            print(result)

        async with session.post(
                f"{base_url}/retrieve_task_memory_simple",
                json={
                    "query": "茅台怎么样？",
                    "workspace_id": workspace_id,
                },
                headers={"Content-Type": "application/json"}
        ) as response:
            result = await response.json()
            print(result)


if __name__ == "__main__":
    asyncio.run(main())

