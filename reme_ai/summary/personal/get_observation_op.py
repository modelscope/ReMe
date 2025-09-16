import re
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory, PersonalMemory
from reme_ai.utils.datetime_handler import DatetimeHandler


@C.register_op()
class GetObservationOp(BaseAsyncOp):
    """
    A specialized operation class to generate observations from chat messages using BaseAsyncOp.
    """
    file_path: str = __file__

    async def async_execute(self):
        """Extract personal observations from chat messages"""
        # Get messages from context - guaranteed to exist by flow input
        messages: List[Message] = self.context.messages
        if not messages:
            logger.warning("No messages found in context")
            return

        # Filter messages - exclude those with time-related keywords
        filtered_messages = self._filter_messages(messages)
        if not filtered_messages:
            logger.warning("No messages left after filtering")
            self.context.observation_memories = []
            return

        logger.info(f"Extracting observations from {len(filtered_messages)} filtered messages")

        # Extract observations using LLM
        observation_memories = await self._extract_observations_from_messages(filtered_messages)

        # Store results in context using standardized key
        self.context.observation_memories = observation_memories
        logger.info(f"Generated {len(observation_memories)} observation memories")

    def _filter_messages(self, messages: List[Message]) -> List[Message]:
        """
        Filters the chat messages to exclude those containing time-related keywords.

        Args:
            messages: List of messages to filter

        Returns:
            List[Message]: A list of filtered messages without time keywords.
        """
        filtered_messages = []
        for msg in messages:
            if not DatetimeHandler.has_time_word(query=msg.content, language=self.language):
                filtered_messages.append(msg)

        logger.info(f"Filtered messages from {len(messages)} to {len(filtered_messages)}")
        return filtered_messages

    async def _extract_observations_from_messages(self, filtered_messages: List[Message]) -> List[BaseMemory]:
        """Extract observations from filtered messages using LLM"""
        user_name = self.context.get("user_name", "user")

        # Build prompt for observation extraction
        user_query_list = []
        for i, msg in enumerate(filtered_messages):
            user_query_list.append(f"{i + 1} {user_name}: {msg.content}")

        # Create prompt using the prompt format method
        system_prompt = self.prompt_format(prompt_name="get_observation_system",
                                           num_obs=len(user_query_list),
                                           user_name=user_name)
        few_shot = self.prompt_format(prompt_name="get_observation_few_shot", user_name=user_name)
        user_query = self.prompt_format(prompt_name="get_observation_user_query",
                                        user_query="\n".join(user_query_list),
                                        user_name=user_name)

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"get_observation_prompt={full_prompt}")

        def parse_observations(message: Message) -> List[BaseMemory]:
            """Parse LLM response and create observation memories"""
            response_text = message.content
            logger.info(f"get_observation_response={response_text}")

            # Parse observations using class method
            parsed_observations = GetObservationOp.parse_observation_response(response_text)

            observation_memories = []
            for obs in parsed_observations:
                idx = obs["index"] - 1  # Convert to 0-based index
                if idx >= len(filtered_messages):
                    logger.warning(f"Invalid index {idx} for messages list of length {len(filtered_messages)}")
                    continue

                # Create observation memory
                observation = PersonalMemory(
                    workspace_id=self.context.workspace_id,
                    when_to_use=obs["keywords"],
                    content=obs["content"],
                    target=user_name,
                    author=self.llm.model_name,
                    metadata={
                        "keywords": obs["keywords"],
                        "source_message": filtered_messages[idx].content,
                        "observation_type": "personal_info"
                    }
                )
                observation_memories.append(observation)
                logger.info(f"Created observation: {obs['content'][:50]}...")

            return observation_memories

        # Use LLM chat with callback function
        return await self.llm.achat(messages=[Message(content=full_prompt)], callback_fn=parse_observations)

    @staticmethod
    def parse_observation_response(response_text: str) -> List[dict]:
        """Parse observation response to extract structured data"""
        # Pattern to match both Chinese and English observation formats
        pattern = r"信息：<(\d+)>\s*<>\s*<([^<>]+)>\s*<([^<>]*)>|Information:\s*<(\d+)>\s*<>\s*<([^<>]+)>\s*<([^<>]*)>"
        matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

        observations = []
        for match in matches:
            # Handle both Chinese and English patterns
            if match[0]:  # Chinese pattern
                idx_str, content, keywords = match[0], match[1], match[2]
            else:  # English pattern  
                idx_str, content, keywords = match[3], match[4], match[5]

            try:
                idx = int(idx_str)
                # Skip if content indicates no meaningful observation
                content_lower = content.lower().strip()
                if content_lower not in ['无', 'none', '', 'repeat']:
                    observations.append({
                        "index": idx,
                        "content": content.strip(),
                        "keywords": keywords.strip() if keywords else ""
                    })
            except ValueError:
                logger.warning(f"Invalid index format: {idx_str}")
                continue

        return observations
