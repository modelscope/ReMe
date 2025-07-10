from typing import List

from experiencemaker.enumeration.role import Role
from experiencemaker.schema.message import Message


def merge_messages_content(messages: List[Message | dict]) -> str:
    content_collector = []
    for i, message in enumerate(messages):
        if isinstance(message, dict):
            message = Message(**message)

        if message.role is Role.ASSISTANT:
            line = f"### step.{i} role={message.role.value} content=\n{message.reasoning_content}\n\n{message.content}\n"
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    line += f" - tool call={tool_call.name}\n   params={tool_call.arguments}\n"
            content_collector.append(line)

        elif message.role is Role.USER:
            line = f"### step.{i} role={message.role.value} content=\n{message.content}\n"
            content_collector.append(line)

        elif message.role is Role.TOOL:
            line = f"### step.{i} role={message.role.value} tool call result=\n{message.content}\n"
            content_collector.append(line)

    return "\n".join(content_collector)
