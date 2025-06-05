from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"  # environment

    ASSISTANT = "assistant"  # policy model
    CONTEXT_ASSISTANT = "context_assistant"  # context model
    SUMMARY_ASSISTANT = "summary_assistant"  # summary model
