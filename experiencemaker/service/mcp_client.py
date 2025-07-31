import asyncio
import json
from typing import List

from fastmcp import Client
from pydantic import BaseModel, Field

from experiencemaker.schema.request import RetrieverRequest, SummarizerRequest, VectorStoreRequest, AgentRequest
from experiencemaker.schema.response import RetrieverResponse, SummarizerResponse, VectorStoreResponse, AgentResponse


class MCPClient(BaseModel):
    base_url: str = Field(default="http://0.0.0.0:8001/sse")
    enable_sse: bool = Field(default=True)
    timeout: int = Field(default=300)

    _client: Client | None = None

    async def __aenter__(self):
        if self.enable_sse:
            self._client = Client(self.base_url)
        else:
            self._client = Client("stdio")

        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self) -> List[str]:
        tools = await self._client.list_tools()
        return [tool.name for tool in tools]

    async def call_retriever(self, request: RetrieverRequest) -> RetrieverResponse:
        result = await self._client.call_tool("retriever", request.model_dump())
        return RetrieverResponse(**result.structured_content)

    async def call_summarizer(self, request: SummarizerRequest) -> SummarizerResponse:
        result = await self._client.call_tool("summarizer", request.model_dump())
        return SummarizerResponse(**result.structured_content)

    async def call_vector_store(self, request: VectorStoreRequest) -> VectorStoreResponse:
        result = await self._client.call_tool("vector_store", request.model_dump())
        return VectorStoreResponse(**result.structured_content)

    async def call_agent(self, request: AgentRequest) -> AgentResponse:
        result = await self._client.call_tool("agent", request.model_dump())
        return AgentResponse(**result.structured_content)


async def main():
    """Example usage of MCPClient"""
    async with MCPClient() as client:
        # List available tools
        tools = await client.list_tools()
        print("Available tools:", json.dumps(tools, ensure_ascii=False, indent=2))

        # Example retriever call
        retriever_request = RetrieverRequest(
            workspace_id="test_workspace",
            query="hello world",
            top_k=5)

        try:
            response = await client.call_retriever(retriever_request)
            print("Retriever response:", response.model_dump())
        except Exception as e:
            print(f"Error calling retriever: {e}")

        # Example summarizer call
        from experiencemaker.schema.message import Trajectory, Message

        summarizer_request = SummarizerRequest(
            workspace_id="test_workspace",
            traj_list=[Trajectory(messages=[Message(content="hello world!")])])

        try:
            response = await client.call_summarizer(summarizer_request)
            print("Summarizer response:", response.model_dump())
        except Exception as e:
            print(f"Error calling summarizer: {e}")


if __name__ == "__main__":
    asyncio.run(main())
