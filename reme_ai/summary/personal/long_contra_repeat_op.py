import re
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory, PersonalMemory


@C.register_op()
class LongContraRepeatOp(BaseAsyncOp):
    """
    Manages and updates memory entries within a conversation scope by identifying
    and handling contradictions or redundancies. It extends BaseAsyncOp to provide
    specialized functionality for long conversations with potential contradictory
    or repetitive statements.
    """
    file_path: str = __file__

    async def async_execute(self):
        """
        Analyze memories for contradictions and redundancies, resolving conflicts.
        
        Process:
        1. Get updated insight memories from previous operation
        2. Check for contradictions and redundancies among memories
        3. Resolve conflicts by keeping most recent/accurate information
        4. Filter out redundant memories
        5. Store cleaned memory list in context
        """
        # Get memories from previous operation
        updated_insights = self.context.response.metadata.get("updated_insight_memories", [])

        if not updated_insights:
            logger.info("No updated insight memories to process for contradictions")
            self.context.response.metadata["memory_list"] = []
            return

        # Get operation parameters
        max_memories_to_process = self.op_params.get("long_contra_repeat_max_count", 50)
        enable_processing = self.op_params.get("enable_long_contra_repeat", True)

        if not enable_processing:
            logger.info("Long contradiction/repeat processing is disabled")
            self.context.response.metadata["memory_list"] = updated_insights
            return

        # Sort memories by creation time (most recent first) and limit count
        sorted_memories = sorted(
            updated_insights,
            key=lambda x: x.time_created,
            reverse=True
        )[:max_memories_to_process]

        if len(sorted_memories) <= 1:
            logger.info("Only one memory to process, skipping contradiction analysis")
            self.context.response.metadata["memory_list"] = sorted_memories
            return

        logger.info(f"Processing {len(sorted_memories)} memories for contradictions and redundancies")

        # Analyze and resolve contradictions
        filtered_memories = await self._analyze_and_resolve_conflicts(sorted_memories)

        # Store results in context
        self.context.response.metadata["memory_list"] = filtered_memories
        logger.info(f"Conflict resolution: {len(sorted_memories)} -> {len(filtered_memories)} memories")

    async def _analyze_and_resolve_conflicts(self, memories: List[BaseMemory]) -> List[BaseMemory]:
        """
        Analyze memories for contradictions and redundancies using LLM.
        
        Args:
            memories: List of memories to analyze
            
        Returns:
            List of filtered memories with conflicts resolved
        """
        user_name = self.context.get("user_name", "user")

        # Prepare memory content for LLM analysis
        memory_texts = []
        for i, memory in enumerate(memories):
            memory_texts.append(f"{i + 1} {memory.content}")

        # Build LLM prompt
        system_prompt = self.prompt_format(
            prompt_name="long_contra_repeat_system",
            num_obs=len(memory_texts),
            user_name=user_name
        )
        few_shot = self.prompt_format(
            prompt_name="long_contra_repeat_few_shot",
            user_name=user_name
        )
        user_query = self.prompt_format(
            prompt_name="long_contra_repeat_user_query",
            user_query="\n".join(memory_texts)
        )

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"Contradiction analysis prompt length: {len(full_prompt)} chars")

        # Get LLM analysis
        response = await self.llm.achat([Message(role=Role.USER, content=full_prompt)])

        if not response or not response.content:
            logger.warning("Empty response from LLM, keeping all memories")
            return memories

        # Parse response and filter memories
        return self._parse_and_filter_memories(response.content, memories, user_name)

    @staticmethod
    def _parse_and_filter_memories(response_text: str, memories: List[BaseMemory], user_name: str) -> List[BaseMemory]:
        """Parse LLM response and filter memories based on contradiction/containment analysis"""

        # Use class method to parse the response
        judgments = LongContraRepeatOp.parse_long_contra_repeat_response(response_text)

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
                        modified_memory.update_time_modified()
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

    @staticmethod
    def parse_long_contra_repeat_response(response_text: str) -> List[tuple]:
        """Parse long contra repeat response to extract judgments"""
        # Pattern to match both Chinese and English judgment formats
        # Chinese: 判断：<序号> <矛盾|被包含|无> <修改后的内容>
        # English: Judgment: <Index> <Contradiction|Contained|None> <Modified content>
        pattern = r"判断：<(\d+)>\s*<(矛盾|被包含|无)>\s*<([^<>]*)>|Judgment:\s*<(\d+)>\s*<(Contradiction|Contained|None)>\s*<([^<>]*)>"
        matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

        judgments = []
        for match in matches:
            # Handle both Chinese and English patterns
            if match[0]:  # Chinese pattern
                idx_str, judgment, modified_content = match[0], match[1], match[2]
            else:  # English pattern
                idx_str, judgment, modified_content = match[3], match[4], match[5]

            try:
                idx = int(idx_str)
                judgments.append((idx, judgment, modified_content))
            except ValueError:
                logger.warning(f"Invalid index format: {idx_str}")
                continue

        logger.info(f"Parsed {len(judgments)} long contra repeat judgments from response")
        return judgments
