from typing import List

from flowllm import C, BaseOp
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class PrintMemoryOp(BaseOp):
    """
    Formats the memories to print.
    """
    file_path: str = __file__

    def execute(self):
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
