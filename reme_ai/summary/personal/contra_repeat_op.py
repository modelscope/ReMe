from typing import List

from flowllm import C, BaseLLMOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class ContraRepeatOp(BaseLLMOp):
    """
    The `ContraRepeatOp` class specializes in processing memory nodes to identify and handle
    contradictory and repetitive information. It extends the base functionality of `BaseLLMOp`.

    Responsibilities:
    - Collects observation memories from context.
    - Constructs a prompt with these observations for language model analysis.
    - Parses the model's response to detect contradictions or redundancies.
    - Filters and returns the processed memories.
    """
    file_path: str = __file__

    def execute(self):
        """
        Executes the primary routine of the ContraRepeatOp which involves:
        1. Gets memory list from context
        2. Constructs a prompt with these memories for language model analysis
        3. Parses the model's response to detect contradictions or redundancies
        4. Filters and returns the processed memories
        """
        # Get memory list from context
        memory_list: List[BaseMemory] = self.context.response.metadata.get("memory_list", [])

        if not memory_list:
            logger.info("memory_list is empty!")
            return

        # Get operation parameters
        contra_repeat_max_count: int = self.op_params.get("contra_repeat_max_count", 50)
        enable_contra_repeat: bool = self.op_params.get("enable_contra_repeat", True)

        if not enable_contra_repeat:
            logger.warning("contra_repeat is not enabled!")
            return

        # Sort and limit memories by count
        sorted_memories = sorted(memory_list, key=lambda x: getattr(x, 'created_at', ''), reverse=True)[
            :contra_repeat_max_count]

        if len(sorted_memories) <= 1:
            logger.info("sorted_memories.size<=1, stop.")
            return

        # Build prompt
        user_query_list = []
        for i, memory in enumerate(sorted_memories):
            user_query_list.append(f"{i + 1} {memory.content}")

        user_name = self.context.get("user_name", "user")

        # Create prompt using the new pattern
        system_prompt = self.prompt_format(prompt_name="contra_repeat_system",
                                           num_obs=len(user_query_list),
                                           user_name=user_name)
        few_shot = self.prompt_format(prompt_name="contra_repeat_few_shot", user_name=user_name)
        user_query = self.prompt_format(prompt_name="contra_repeat_user_query",
                                        user_query="\n".join(user_query_list))

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"contra_repeat_prompt={full_prompt}")

        # Call LLM
        response = self.llm.chat([Message(role=Role.USER, content=full_prompt)])

        # Return if empty
        if not response or not response.content:
            logger.warning("Empty response from LLM")
            return

        response_text = response.content
        logger.info(f"contra_repeat_response={response_text}")

        # Parse response and filter memories
        filtered_memories = self._parse_and_filter_memories(response_text, sorted_memories, user_name)

        # Update context with filtered memories
        self.context.response.metadata["memory_list"] = filtered_memories
        logger.info(f"Filtered {len(memory_list)} memories to {len(filtered_memories)} memories")

    def _parse_and_filter_memories(self, response_text: str, memories: List[BaseMemory], user_name: str) -> List[
        BaseMemory]:
        """Parse LLM response and filter memories based on contradiction/containment analysis"""
        import re

        # Parse the response to extract judgments
        pattern = r"<(\d+)>\s*<(矛盾|被包含|无|Contradiction|Contained|None)>"
        matches = re.findall(pattern, response_text, re.IGNORECASE)

        if not matches:
            logger.warning("No valid judgments found in response")
            return memories

        # Create a set of indices to remove (contradictory or contained memories)
        indices_to_remove = set()

        for idx_str, judgment in matches:
            try:
                idx = int(idx_str) - 1  # Convert to 0-based index
                if idx >= len(memories):
                    logger.warning(f"Invalid index {idx} for memories list of length {len(memories)}")
                    continue

                judgment_lower = judgment.lower()
                if judgment_lower in ['矛盾', 'contradiction', '被包含', 'contained']:
                    indices_to_remove.add(idx)
                    logger.info(f"Marking memory {idx + 1} for removal: {judgment} - {memories[idx].content[:100]}...")

            except ValueError:
                logger.warning(f"Invalid index format: {idx_str}")
                continue

        # Filter out the memories marked for removal
        filtered_memories = [memory for i, memory in enumerate(memories) if i not in indices_to_remove]

        return filtered_memories

    def get_language_value(self, value_dict: dict):
        """Get language-specific value from dictionary"""
        return value_dict.get(self.language, value_dict.get("en"))
