import re
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.message import Message, Trajectory
from loguru import logger

from reme_ai.schema.memory import PersonalMemory


@C.register_op()
class InfoFilterOp(BaseAsyncOp):
    """
    A specialized operation class to filter messages based on information content scores using BaseAsyncOp.
    This filters chat messages by retaining only those that include significant information about the user.
    """
    file_path: str = __file__

    async def async_execute(self):
        """Filter messages based on information content scores"""
        # Get messages from context - guaranteed to exist by flow input
        trajectories: list = self.context.trajectories
        trajectories: List[Trajectory] = [Trajectory(**x) if isinstance(x, dict) else x for x in trajectories]

        self.context.messages = []
        for trajectory in trajectories:
            self.context.messages.extend(trajectory.messages)
        messages: List[Message] = self.context.messages
        if not messages:
            logger.warning("No messages found in context")
            return

        # Get operation parameters
        preserved_scores = self.op_params.get("preserved_scores", "2,3")
        info_filter_msg_max_size = self.op_params.get("info_filter_msg_max_size", 200)
        user_name = self.context.get("user_name", "user")

        # Filter and process messages
        info_messages = self._filter_and_process_messages(messages, user_name, info_filter_msg_max_size)
        if not info_messages:
            logger.warning("No messages left after filtering")
            self.context.messages = []
            return

        logger.info(f"Filtering {len(info_messages)} messages for information content")

        # Filter messages using LLM
        filtered_memories = await self._filter_messages_with_llm(info_messages, user_name, preserved_scores)

        # Store results in context using standardized key
        self.context.messages = filtered_memories
        logger.info(f"Filtered to {len(filtered_memories)} high-information messages")

    @staticmethod
    def _filter_and_process_messages(messages: List[Message], user_name: str, max_size: int) -> List[Message]:
        """Filter and process messages for information filtering"""
        info_messages = []

        for msg in messages:
            # Ensure metadata exists

            # Skip memorized messages
            if msg.metadata.get('memorized', False):
                continue

            # Only process messages from the target user
            # role_name = msg.metadata.get('role_name')
            # if role_name and role_name != user_name:
            #     continue

            elif msg.role.value != "user":
                continue

            # Truncate long messages
            if len(msg.content) >= max_size:
                half_size = int(max_size * 0.5 + 0.5)
                msg.content = msg.content[:half_size] + msg.content[-half_size:]

            info_messages.append(msg)

        logger.info(f"Filtered messages from {len(messages)} to {len(info_messages)}")
        return info_messages

    async def _filter_messages_with_llm(self, info_messages: List[Message], user_name: str, preserved_scores: str) -> List[
        PersonalMemory]:
        """Filter messages using LLM to score information content"""

        # Build prompt for information filtering
        user_query_list = []
        colon = self._get_colon_word()
        for i, msg in enumerate(info_messages):
            user_query_list.append(f"{i + 1} {user_name}{colon} {msg.content}")

        # Create prompt using the prompt format method
        system_prompt = self.prompt_format(prompt_name="info_filter_system",
                                           batch_size=len(info_messages),
                                           user_name=user_name)
        few_shot = self.prompt_format(prompt_name="info_filter_few_shot", user_name=user_name)
        user_query = self.prompt_format(prompt_name="info_filter_user_query",
                                        user_query="\n".join(user_query_list))

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"info_filter_prompt={full_prompt}")

        def parse_and_filter(message: Message) -> List[PersonalMemory]:
            """Parse LLM response and create filtered memories"""
            response_text = message.content
            logger.info(f"info_filter_response={response_text}")

            # Parse scores using class method
            info_scores = InfoFilterOp.parse_info_filter_response(response_text)

            if len(info_scores) != len(info_messages):
                logger.warning(f"score_size != messages_size, {len(info_scores)} vs {len(info_messages)}")

            filtered_memories = []
            for idx, score in info_scores:
                # Convert to 0-based index
                msg_idx = idx - 1
                if msg_idx >= len(info_messages):
                    logger.warning(f"Invalid index {msg_idx} for messages list of length {len(info_messages)}")
                    continue

                # Check if score should be preserved
                if score in preserved_scores:
                    message = info_messages[msg_idx]

                    # Create memory from filtered message with combined metadata
                    memory = PersonalMemory(
                        workspace_id=self.context.get("workspace_id", ""),
                        content=message.content,
                        target=user_name,
                        author=getattr(self.llm, "model_name", "system"),
                        metadata={
                            "info_score": score,
                            "filter_type": "info_content",
                            "original_message_time": getattr(message, 'time_created', None),
                            "role_name": message.metadata.pop("role_name", user_name),
                            "memorized": True,
                            **message.metadata  # Include all original metadata
                        }
                    )
                    filtered_memories.append(memory)
                    logger.info(f"Info filter: kept message with score {score}: {message.content[:50]}...")

            return filtered_memories

        # Use LLM chat with callback function
        return await self.llm.achat(messages=[Message(content=full_prompt)], callback_fn=parse_and_filter)

    def _get_colon_word(self) -> str:
        """Get language-specific colon word"""
        colon_dict = {"zh": "：", "cn": "：", "en": ": "}
        return colon_dict.get(self.language, ": ")

    @staticmethod
    def parse_info_filter_response(response_text: str) -> List[tuple]:
        """Parse info filter response to extract message scores"""
        # Pattern to match both Chinese and English result formats
        # Chinese: 结果：<序号> <分数>
        # English: Result: <Index> <Score>
        pattern = r"结果：<(\d+)>\s*<([0-3])>|Result:\s*<(\d+)>\s*<([0-3])>"
        matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

        scores = []
        for match in matches:
            # Handle both Chinese and English patterns
            if match[0]:  # Chinese pattern
                idx_str, score_str = match[0], match[1]
            else:  # English pattern
                idx_str, score_str = match[2], match[3]

            try:
                idx = int(idx_str)
                score = score_str
                scores.append((idx, score))
            except ValueError:
                logger.warning(f"Invalid index or score format: {idx_str}, {score_str}")
                continue

        logger.info(f"Parsed {len(scores)} info filter scores from response")
        return scores
