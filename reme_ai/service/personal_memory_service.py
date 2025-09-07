import asyncio
from typing import Optional, Dict, Any, List

from flowllm import C
from flowllm.flow import BaseToolFlow
from flowllm.schema.flow_response import FlowResponse
from loguru import logger
from pydantic import Field, BaseModel

from reme_ai.config.config_parser import ConfigParser
from reme_ai.schema.memory import PersonalMemory
from reme_ai.service.base_memory_service import BaseMemoryService


class PersonalMemoryService(BaseMemoryService):

    async def start(self) -> None:
        C.set_service_config(parser=ConfigParser, config_name="config=default").init_by_service_config()

    async def stop(self) -> None:
        C.stop_by_service_config()

    async def health(self) -> bool:
        return True

    async def add_memory(self, user_id: str, messages: list, session_id: Optional[str] = None) -> None:
        summary_flow: BaseToolFlow = C.flow_dict["summary_personal_memory"]

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

        result: FlowResponse = await summary_flow(**kwargs)
        memory_list: List[PersonalMemory] = result.metadata.get("memory_list", [])
        for memory in memory_list:
            memory_id = memory.memory_id
            self.add_session_memory_id(session_id, memory_id)
            logger.info(f"[personal_memory_service] user_id={user_id} session_id={session_id} add memory: {memory}")

    async def search_memory(self, user_id: str, messages: list, filters: Optional[Dict[str, Any]] = Field(
        description="Associated filters for the messages, "
                    "such as top_k, score etc.",
        default=None,
    )) -> list:

        retrieve_flow: BaseToolFlow = C.flow_dict["retrieve_personal_memory"]

        new_messages: List[dict] = []
        for message in messages:
            if isinstance(message, dict):
                new_messages.append(message)
            elif isinstance(message, BaseModel):
                new_messages.append(message.model_dump())
            else:
                raise ValueError(f"Invalid message type={type(message)}")

        # Extract query from the last message
        query = new_messages[-1]["content"] if messages else ""

        kwargs = {
            "workspace_id": user_id,
            "query": query,
            "top_k": filters.get("top_k", 1) if filters else 1
        }

        result: FlowResponse = await retrieve_flow(**kwargs)
        logger.info(f"[personal_memory_service] user_id={user_id} search result: {result.model_dump_json()}")

        return [result.answer]

    async def list_memory(self, user_id: str, filters: Optional[Dict[str, Any]] = Field(
        description="Associated filters for the messages, "
                    "such as top_k, score etc.",
        default=None,
    )) -> list:
        vector_store_flow: BaseToolFlow = C.flow_dict["vector_store"]
        result = await vector_store_flow(workspace_id=user_id, action="list")
        logger.info(f"[personal_memory_service] list_memory result: {result}")

        result = result.metadata["action_result"]
        for i, line in enumerate(result):
            logger.info(f"[personal_memory_service] list memory.{i}={line}")
        return result

    async def delete_memory(self, user_id: str, session_id: Optional[str] = None) -> None:
        delete_ids = self.session_id_dict.get(session_id, [])
        if not delete_ids:
            return

        vector_store_flow: BaseToolFlow = C.flow_dict["vector_store"]
        result = await vector_store_flow(workspace_id=user_id, action="delete_ids", memory_ids=delete_ids)
        result = result.metadata["action_result"]
        logger.info(f"[personal_memory_service] delete memory result={result}")


async def main():
    async with PersonalMemoryService() as service:
        logger.info("========== start personal memory service ==========")

        await service.add_memory(user_id="u_12345",
                                 messages=[{"content": "I really enjoy playing tennis on weekends"}],
                                 session_id="s_123456")

        await service.search_memory(user_id="u_12345",
                                    messages=[{"content": "What do I like to do for fun?"}],
                                    filters={"top_k": 1})

        await service.list_memory(user_id="u_12345")
        await service.delete_memory(user_id="u_12345", session_id="s_123456")
        await service.list_memory(user_id="u_12345")

        logger.info("========== end personal memory service ==========")


if __name__ == "__main__":
    asyncio.run(main())
