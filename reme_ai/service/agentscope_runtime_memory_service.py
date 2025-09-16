from abc import abstractmethod, ABC
from typing import Optional, Dict, Any

from flowllm import FlowLLMApp
from pydantic import Field

from reme_ai.config.config_parser import ConfigParser


class AgentscopeRuntimeMemoryService(ABC):

    def __init__(self):
        self.app = FlowLLMApp(parser=ConfigParser, load_default_config=True)
        self.session_id_dict: dict = {}

    def add_session_memory_id(self, session_id: str, memory_id):
        if session_id not in self.session_id_dict:
            self.session_id_dict[session_id] = []

        self.session_id_dict[session_id].append(memory_id)

    @abstractmethod
    async def start(self) -> None:
        """Starts the service, initializing any necessary resources or
        connections."""

    @abstractmethod
    async def stop(self) -> None:
        """Stops the service, releasing any acquired resources."""

    @abstractmethod
    async def health(self) -> bool:
        """
        Checks the health of the service.

        Returns:
            True if the service is healthy, False otherwise.
        """

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        return False

    @abstractmethod
    async def add_memory(
            self,
            user_id: str,
            messages: list,
            session_id: Optional[str] = None,
    ) -> None:
        """
        Adds messages to the memory service.

        Args:
            user_id: The user id.
            messages: The messages to add.
            session_id: The session id, which is optional.
        """

    @abstractmethod
    async def search_memory(
            self,
            user_id: str,
            messages: list,
            filters: Optional[Dict[str, Any]] = Field(
                description="Associated filters for the messages, "
                            "such as top_k, score etc.",
                default=None,
            ),
    ) -> list:
        """
        Searches messages from the memory service.

        Args:
            user_id: The user id.
            messages: The user query or the query with history messages,
                both in the format of list of messages.  If messages is a list,
                the search will be based on the content of the last message.
            filters: The filters used to search memory
        """

    @abstractmethod
    async def list_memory(
            self,
            user_id: str,
            filters: Optional[Dict[str, Any]] = Field(
                description="Associated filters for the messages, "
                            "such as top_k, score etc.",
                default=None,
            ),
    ) -> list:
        """
        Lists the memory items for a given user with filters, such as
        page_num, page_size, etc.

        Args:
            user_id: The user id.
            filters: The filters for the memory items.
        """

    @abstractmethod
    async def delete_memory(
            self,
            user_id: str,
            session_id: Optional[str] = None,
    ) -> None:
        """
        Deletes the memory items for a given user with certain session id,
        or all the memory items for a given user.
        """
