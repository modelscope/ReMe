from typing import List

from flowllm import C, BaseLLMOp
from loguru import logger

from reme_ai.schema.memory import PersonalMemory
from reme_ai.utils.datetime_handler import DatetimeHandler
from reme_ai.utils.op_utils import load_memories_from_vector_store


@C.register_op()
class LoadMemoryOp(BaseLLMOp):
    """
    A specialized operation class to load various types of personal memories using BaseLLMOp.
    This loads different categories of memories including observations, insights, and recent memories.
    """
    file_path: str = __file__

    def execute(self):
        """
        Executes the main routine of the LoadMemoryOp. This involves loading various types
        of personal memories based on the configuration parameters.
        """
        # Get operation parameters
        retrieve_not_reflected_top_k: int = self.op_params.get("retrieve_not_reflected_top_k", 0)
        retrieve_not_updated_top_k: int = self.op_params.get("retrieve_not_updated_top_k", 0)
        retrieve_insight_top_k: int = self.op_params.get("retrieve_insight_top_k", 0)
        retrieve_today_top_k: int = self.op_params.get("retrieve_today_top_k", 0)

        # Get context parameters
        workspace_id = self.context.get("workspace_id", "")
        user_name = self.context.get("user_name", "user")

        logger.info(f"Loading memories for user: {user_name} in workspace: {workspace_id}")

        # Load different types of memories
        all_memories = []

        # Load not reflected memories
        if retrieve_not_reflected_top_k > 0:
            not_reflected_memories = self._retrieve_not_reflected_memories(
                workspace_id, user_name, retrieve_not_reflected_top_k
            )
            all_memories.extend(not_reflected_memories)
            logger.info(f"Loaded {len(not_reflected_memories)} not reflected memories")

        # Load not updated memories
        if retrieve_not_updated_top_k > 0:
            not_updated_memories = self._retrieve_not_updated_memories(
                workspace_id, user_name, retrieve_not_updated_top_k
            )
            all_memories.extend(not_updated_memories)
            logger.info(f"Loaded {len(not_updated_memories)} not updated memories")

        # Load insight memories
        if retrieve_insight_top_k > 0:
            insight_memories = self._retrieve_insight_memories(
                workspace_id, user_name, retrieve_insight_top_k
            )
            all_memories.extend(insight_memories)
            logger.info(f"Loaded {len(insight_memories)} insight memories")

        # Load today's memories
        if retrieve_today_top_k > 0:
            today_memories = self._retrieve_today_memories(
                workspace_id, user_name, retrieve_today_top_k
            )
            all_memories.extend(today_memories)
            logger.info(f"Loaded {len(today_memories)} today's memories")

        # Store results in context
        self.context.response.metadata["loaded_memories"] = all_memories
        self.context.response.metadata["not_reflected_memories"] = [
            m for m in all_memories if m.metadata.get("memory_category") == "not_reflected"
        ]
        self.context.response.metadata["not_updated_memories"] = [
            m for m in all_memories if m.metadata.get("memory_category") == "not_updated"
        ]
        self.context.response.metadata["insight_memories"] = [
            m for m in all_memories if m.metadata.get("memory_category") == "insight"
        ]
        self.context.response.metadata["today_memories"] = [
            m for m in all_memories if m.metadata.get("memory_category") == "today"
        ]

        logger.info(f"Total memories loaded: {len(all_memories)}")

    def _retrieve_not_reflected_memories(self, workspace_id: str, user_name: str, top_k: int) -> List[PersonalMemory]:
        """
        Retrieves top-K not reflected memories based on the query.
        """
        filter_criteria = {
            "memory_type": "personal",
            "target": user_name,
            "reflected": False
        }

        memories = load_memories_from_vector_store(
            workspace_id=workspace_id,
            filter_criteria=filter_criteria,
            top_k=top_k,
            memory_category="not_reflected"
        )

        return memories

    def _retrieve_not_updated_memories(self, workspace_id: str, user_name: str, top_k: int) -> List[PersonalMemory]:
        """
        Retrieves top-K not updated memories based on the query.
        """
        filter_criteria = {
            "memory_type": "personal",
            "target": user_name,
            "updated": False
        }

        memories = load_memories_from_vector_store(
            workspace_id=workspace_id,
            filter_criteria=filter_criteria,
            top_k=top_k,
            memory_category="not_updated"
        )

        return memories

    def _retrieve_insight_memories(self, workspace_id: str, user_name: str, top_k: int) -> List[PersonalMemory]:
        """
        Retrieves top-K insight memories based on the query.
        """
        filter_criteria = {
            "memory_type": "personal_insight",
            "target": user_name
        }

        memories = load_memories_from_vector_store(
            workspace_id=workspace_id,
            filter_criteria=filter_criteria,
            top_k=top_k,
            memory_category="insight"
        )

        return memories

    def _retrieve_today_memories(self, workspace_id: str, user_name: str, top_k: int) -> List[PersonalMemory]:
        """
        Retrieves top-K memories from today based on the query.
        """
        # Get today's date
        dt = DatetimeHandler().datetime_format()
        today_date = dt.split()[0]  # Extract date part

        filter_criteria = {
            "memory_type": "personal",
            "target": user_name,
            "created_date": today_date
        }

        memories = load_memories_from_vector_store(
            workspace_id=workspace_id,
            filter_criteria=filter_criteria,
            top_k=top_k,
            memory_category="today"
        )

        return memories
