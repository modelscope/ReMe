import asyncio
from typing import Optional, Dict, Any, List

from flowllm.schema.flow_response import FlowResponse
from loguru import logger
from pydantic import Field, BaseModel

from reme_ai.schema.memory import TaskMemory
from reme_ai.service.agentscope_runtime_memory_service import AgentscopeRuntimeMemoryService


class TaskMemoryService(AgentscopeRuntimeMemoryService):

    async def start(self):
        return await self.app.async_start()

    async def stop(self) -> None:
        return await self.app.async_stop()

    async def health(self) -> bool:
        return True

    async def add_memory(self, user_id: str, messages: list, session_id: Optional[str] = None) -> None:
        new_messages: List[dict] = []
        for message in messages:
            if isinstance(message, dict):
                new_messages.append(message)
            elif isinstance(message, BaseModel):
                new_messages.append(message.model_dump())
            else:
                raise ValueError(f"Invalid message type={type(message)}")

        kwargs = {
            "workspace_id": user_id,
            "trajectories": [
                {"messages": new_messages, "score": 1.0}
            ]
        }

        result: FlowResponse = await self.app.async_execute_flow(name="summary_task_memory", **kwargs)
        memory_list: List[TaskMemory] = result.metadata.get("memory_list", [])
        for memory in memory_list:
            memory_id = memory.memory_id
            self.add_session_memory_id(session_id, memory_id)
            logger.info(f"[task_memory_service] user_id={user_id} session_id={session_id} add memory: {memory}")

    async def search_memory(self, user_id: str, messages: list, filters: Optional[Dict[str, Any]] = Field(
        description="Associated filters for the messages, "
                    "such as top_k, score etc.",
        default=None,
    )) -> list:
        new_messages: List[dict] = []
        for message in messages:
            if isinstance(message, dict):
                new_messages.append(message)
            elif isinstance(message, BaseModel):
                new_messages.append(message.model_dump())
            else:
                raise ValueError(f"Invalid message type={type(message)}")

        kwargs = {
            "workspace_id": user_id,
            "messages": new_messages,
            "top_k": filters.get("top_k", 1) if filters else 1
        }

        result: FlowResponse = await self.app.async_execute_flow(name="retrieve_task_memory", **kwargs)
        logger.info(f"[task_memory_service] user_id={user_id} add result: {result.model_dump_json()}")

        return [result.answer]

    async def list_memory(self, user_id: str, filters: Optional[Dict[str, Any]] = Field(
        description="Associated filters for the messages, "
                    "such as top_k, score etc.",
        default=None,
    )) -> list:
        result = await self.app.async_execute_flow(name="vector_store", workspace_id=user_id, action="list")
        print("list_memory result:", result)

        result = result.metadata["action_result"]
        for i, line in enumerate(result):
            logger.info(f"[task_memory_service] list memory.{i}={line}")
        return result

    async def delete_memory(self, user_id: str, session_id: Optional[str] = None) -> None:
        delete_ids = self.session_id_dict.get(session_id, [])
        if not delete_ids:
            return

        result = await self.app.async_execute_flow(name="vector_store",
                                                   workspace_id=user_id,
                                                   action="delete_ids",
                                                   memory_ids=delete_ids)
        result = result.metadata["action_result"]
        logger.info(f"[task_memory_service] delete memory result={result}")


async def main():
    async with TaskMemoryService() as service:
        logger.info("========== start task memory service ==========")

        await service.add_memory(user_id="u_123456",
                                 messages=[{"content": "please use web search tool to search financial news:"}],
                                 session_id="s_123456")

        await service.search_memory(user_id="u_123456",
                                    messages=[{"content": "please use web search tool to search financial news"}],
                                    filters={"top_k": 1})

        await service.list_memory(user_id="u_123456")
        await service.delete_memory(user_id="u_123456", session_id="s_123456")
        await service.list_memory(user_id="u_123456")

        logger.info("========== end task memory service ==========")


if __name__ == "__main__":
    asyncio.run(main())
