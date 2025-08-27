from typing import List

from flowllm import C, BaseLLMOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory, PersonalMemory
from reme_ai.utils.op_utils import parse_long_contra_repeat_response


@C.register_op()
class LongContraRepeatOp(BaseLLMOp):
    """
    Manages and updates memory entries within a conversation scope by identifying
    and handling contradictions or redundancies. It extends BaseLLMOp to provide
    specialized functionality for long conversations with potential contradictory
    or repetitive statements.
    """
    file_path: str = __file__

    def execute(self):
        """
        Executes the primary routine of the LongContraRepeatOp which involves:
        1. Gets memory list from context
        2. Retrieves similar memories for each memory
        3. Constructs a prompt with these memories for language model analysis
        4. Parses the model's response to detect contradictions or redundancies
        5. Filters and returns the processed memories
        """
        # Get memory list from context
        memory_list: List[BaseMemory] = self.context.response.metadata.get("memory_list", [])

        if not memory_list:
            logger.info("memory_list is empty!")
            return

        # Get operation parameters
        long_contra_repeat_max_count: int = self.op_params.get("long_contra_repeat_max_count", 50)
        enable_long_contra_repeat: bool = self.op_params.get("enable_long_contra_repeat", True)

        if not enable_long_contra_repeat:
            logger.warning("long_contra_repeat is not enabled!")
            return

        # Sort and limit memories by count
        sorted_memories = sorted(memory_list, key=lambda x: getattr(x, 'created_time', ''), reverse=True)[
            :long_contra_repeat_max_count]

        if len(sorted_memories) <= 1:
            logger.info("sorted_memories.size<=1, stop.")
            return

        # Build prompt
        user_query_list = []
        for i, memory in enumerate(sorted_memories):
            user_query_list.append(f"{i + 1} {memory.content}")

        user_name = self.context.get("user_name", "user")

        # Create prompt using the new pattern
        system_prompt = self.prompt_format(prompt_name="long_contra_repeat_system",
                                           num_obs=len(user_query_list),
                                           user_name=user_name)
        few_shot = self.prompt_format(prompt_name="long_contra_repeat_few_shot", user_name=user_name)
        user_query = self.prompt_format(prompt_name="long_contra_repeat_user_query",
                                        user_query="\n".join(user_query_list))

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"long_contra_repeat_prompt={full_prompt}")

        # Call LLM
        response = self.llm.chat([Message(role=Role.USER, content=full_prompt)])

        # Return if empty
        if not response or not response.content:
            logger.warning("Empty response from LLM")
            return

        response_text = response.content
        logger.info(f"long_contra_repeat_response={response_text}")

        # Parse response and filter memories
        filtered_memories = self._parse_and_filter_memories(response_text, sorted_memories, user_name)

        # Update context with filtered memories
        self.context.response.metadata["memory_list"] = filtered_memories
        logger.info(f"Filtered {len(memory_list)} memories to {len(filtered_memories)} memories")

    def _parse_and_filter_memories(self, response_text: str, memories: List[BaseMemory], user_name: str) -> List[
        BaseMemory]:
        """Parse LLM response and filter memories based on contradiction/containment analysis"""

        # Use utility function to parse the response
        judgments = parse_long_contra_repeat_response(response_text)

        if not judgments:
            logger.warning("No valid judgments found in response")
            return memories

        # Process each judgment
        filtered_memories = []
        processed_indices = set()

        for idx, judgment, modified_content in judgments:
            try:
                memory_idx = idx - 1  # Convert to 0-based index
                if memory_idx >= len(memories):
                    logger.warning(f"Invalid index {memory_idx} for memories list of length {len(memories)}")
                    continue

                processed_indices.add(memory_idx)
                memory = memories[memory_idx]
                judgment_lower = judgment.lower()

                if judgment_lower in ['矛盾', 'contradiction']:
                    # For contradictory memories, either modify content or mark for removal
                    if modified_content.strip():
                        # Create new memory with modified content
                        modified_memory = PersonalMemory(
                            workspace_id=memory.workspace_id,
                            memory_id=memory.memory_id,
                            content=modified_content.strip(),
                            target=memory.target if hasattr(memory, 'target') else user_name,
                            author=memory.author,
                            metadata={**memory.metadata, 'modified_by': 'long_contra_repeat'}
                        )
                        modified_memory.update_modified_time()
                        filtered_memories.append(modified_memory)
                        logger.info(f"Modified contradictory memory {idx}: {modified_content.strip()[:50]}...")
                    else:
                        # Remove contradictory memory without modification
                        logger.info(f"Removing contradictory memory {idx}: {memory.content[:50]}...")

                elif judgment_lower in ['被包含', 'contained']:
                    # Remove contained/redundant memories
                    logger.info(f"Removing contained memory {idx}: {memory.content[:50]}...")

                else:  # 'none' case
                    # Keep the memory as is
                    filtered_memories.append(memory)

            except Exception as e:
                logger.warning(f"Error processing judgment for index {idx}: {e}")
                continue

        # Add any memories that weren't processed (shouldn't happen with correct LLM response)
        for i, memory in enumerate(memories):
            if i not in processed_indices:
                filtered_memories.append(memory)
                logger.warning(f"Memory {i + 1} was not processed by LLM, keeping as is")

        return filtered_memories

    def get_language_value(self, value_dict: dict):
        """Get language-specific value from dictionary"""
        return value_dict.get(self.language, value_dict.get("en"))
