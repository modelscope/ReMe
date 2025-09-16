from typing import List

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class PrintMemoryOp(BaseAsyncOp):
    """
    Formats the memories to print.
    """
    file_path: str = __file__

    async def async_execute(self):
        """
        Executes the primary function, it involves:
        1. Fetches the memories.
        2. Formats them for printing.
        3. Set the formatted string back into the context
        """
        # Get memory list from context
        memory_list: List[BaseMemory] = self.context.response.metadata.get("memory_list", [])

        if not memory_list:
            logger.info("No memories to print")
            self.context.response.answer = "No memories found."
            return

        logger.info(f"Formatting {len(memory_list)} memories for printing")

        # Format memories for printing
        formatted_memories = self._format_memories_for_print(memory_list)

        # Store result in context
        self.context.response.answer = formatted_memories
        logger.info(f"Formatted memories: {formatted_memories}")

    @staticmethod
    def _format_memories_for_print(memories: List[BaseMemory]) -> str:
        """Format memories for printing"""
        if not memories:
            return "No memories available."

        formatted_memories = []

        for i, memory in enumerate(memories, 1):
            memory_text = f"Memory {i}:\n"
            memory_text += f"  When to use: {memory.when_to_use}\n"
            memory_text += f"  Content: {memory.content}\n"

            # Add additional metadata if available
            if hasattr(memory, 'metadata') and memory.metadata:
                metadata_items = []
                for key, value in memory.metadata.items():
                    if key not in ['when_to_use', 'content']:
                        metadata_items.append(f"{key}: {value}")
                if metadata_items:
                    memory_text += f"  Metadata: {', '.join(metadata_items)}\n"

            formatted_memories.append(memory_text)

        return "\n".join(formatted_memories)

    @staticmethod
    def format_memories_for_output(memories: List) -> str:
        """
        Format memory list for output string.
        
        Args:
            memories: List of memory objects
            
        Returns:
            Formatted string
        """
        if not memories:
            return ""

        formatted_parts = []
        for i, memory in enumerate(memories, 1):
            when_to_use = getattr(memory, 'when_to_use', '') or memory.get('when_to_use', '')
            content = getattr(memory, 'content', '') or memory.get('content', '')

            part = f"Memory {i}:\n"
            if when_to_use:
                part += f"When to use: {when_to_use}\n"
            if content:
                part += f"Content: {content}\n"

            formatted_parts.append(part)

        return "\n".join(formatted_parts)

    @staticmethod
    def format_memories_for_simple_output(memories: List) -> str:
        """
        Format memory list for simple flow output.
        
        Args:
            memories: List of memory objects
            
        Returns:
            Formatted string suitable for response.answer
        """
        if not memories:
            return "No relevant memories found."

        content_parts = ["Previous Memory"]

        for memory in memories:
            # Safely get field values
            when_to_use = getattr(memory, 'when_to_use', '') or memory.get('when_to_use', '')
            content = getattr(memory, 'content', '') or memory.get('content', '')

            # Skip memories with empty content
            if not content:
                continue

            # Format individual memory
            memory_text = f"- when_to_use: {when_to_use}\n  content: {content}"
            content_parts.append(memory_text)

        # If no valid memories, return empty message
        if len(content_parts) == 1:  # Only title
            return "No relevant memories with valid content found."

        content_parts.append("\nPlease consider the helpful parts from these in answering the question, "
                             "to make the response more comprehensive and substantial.")

        return "\n".join(content_parts)
