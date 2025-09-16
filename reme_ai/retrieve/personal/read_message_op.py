from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.message import Message
from loguru import logger


@C.register_op()
class ReadMessageOp(BaseAsyncOp):
    """
    Fetches unmemorized chat messages.
    """
    file_path: str = __file__

    async def async_execute(self):
        """
        Executes the primary function to fetch unmemorized chat messages.
        """
        # Get chat messages from context
        chat_messages = self.context.chat_messages
        target_name = self.context.target_name
        contextual_msg_max_count = self.op_params.get('contextual_msg_max_count', 10)

        chat_messages_not_memorized: List[List[Message]] = []
        for messages in chat_messages:
            if not messages:
                continue

            if hasattr(messages[0], 'memorized') and messages[0].memorized:
                continue

            contain_flag = False

            for msg in messages:
                if hasattr(msg, 'role_name') and msg.role_name == target_name:
                    contain_flag = True
                    break

            if contain_flag:
                chat_messages_not_memorized.append(messages)

        chat_message_scatter = []
        for messages in chat_messages_not_memorized[-contextual_msg_max_count:]:
            chat_message_scatter.extend(messages)

        # Sort by time_created if available
        if chat_message_scatter and hasattr(chat_message_scatter[0], 'time_created'):
            chat_message_scatter.sort(key=lambda _: _.time_created)

        # Store result in context
        self.context.chat_messages = chat_message_scatter
        logger.info(f"Retrieved {len(chat_message_scatter)} unmemorized chat messages")
