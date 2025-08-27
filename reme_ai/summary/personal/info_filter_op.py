from typing import List

from flowllm import C, BaseLLMOp
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import PersonalMemory
from reme_ai.utils.op_utils import parse_info_filter_response


@C.register_op()
class InfoFilterOp(BaseLLMOp):
    """
    A specialized operation class to filter messages based on information content scores using BaseLLMOp.
    This filters chat messages by retaining only those that include significant information about the user.
    """
    file_path: str = __file__

    def execute(self):
        """Filter messages based on information content scores"""
        # Get messages from context
        messages: List[Message] = self.context.get("messages", [])
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
            return

        logger.info(f"Filtering {len(info_messages)} messages for information content")

        # Filter messages using LLM
        filtered_memories = self._filter_messages_with_llm(info_messages, user_name, preserved_scores)

        # Store results in context
        self.context.response.metadata["filtered_memories"] = filtered_memories
        logger.info(f"Filtered to {len(filtered_memories)} high-information messages")

    def _filter_and_process_messages(self, messages: List[Message], user_name: str, max_size: int) -> List[Message]:
        """Filter and process messages for information filtering"""
        info_messages = []

        for msg in messages:
            # Skip memorized messages
            if hasattr(msg, 'memorized') and msg.memorized:
                continue

            # Only process messages from the target user
            if hasattr(msg, 'role_name') and msg.role_name != user_name:
                continue
            elif hasattr(msg, 'role') and msg.role != 'user':
                continue

            # Truncate long messages
            if len(msg.content) >= max_size:
                half_size = int(max_size * 0.5 + 0.5)
                msg.content = msg.content[:half_size] + msg.content[-half_size:]

            info_messages.append(msg)

        logger.info(f"Filtered messages from {len(messages)} to {len(info_messages)}")
        return info_messages

    def _filter_messages_with_llm(self, info_messages: List[Message], user_name: str, preserved_scores: str) -> List[
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

            # Parse scores using utility function
            info_scores = parse_info_filter_response(response_text)

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
                    message_obj = info_messages[msg_idx]

                    # Create memory from filtered message
                    memory = PersonalMemory(
                        workspace_id=self.context.get("workspace_id", ""),
                        content=message_obj.content,
                        target=user_name,
                        author=getattr(self.llm, "model_name", "system"),
                        metadata={
                            "info_score": score,
                            "filter_type": "info_content",
                            "original_message_time": getattr(message_obj, 'time_created', None)
                        }
                    )
                    filtered_memories.append(memory)
                    logger.info(f"Info filter: kept message with score {score}: {message_obj.content[:50]}...")

            return filtered_memories

        # Use LLM chat with callback function
        return self.llm.chat(messages=[Message(content=full_prompt)], callback_fn=parse_and_filter)

    def _get_colon_word(self) -> str:
        """Get language-specific colon word"""
        colon_dict = {"zh": "：", "cn": "：", "en": ": "}
        return colon_dict.get(self.language, ": ")
