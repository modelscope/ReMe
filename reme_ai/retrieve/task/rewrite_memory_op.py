import json
import re
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class RewriteMemoryOp(BaseAsyncOp):
    """
    Generate and rewrite context messages from reranked experiences
    """
    file_path: str = __file__

    async def async_execute(self):
        """Execute rewrite operation"""
        memory_list: List[BaseMemory] = self.context.response.metadata["memory_list"]
        query: str = self.context.query
        messages: List[Message] = \
            [Message(**x) if isinstance(x, dict) else x for x in self.context.get('messages', [])]

        if not memory_list:
            logger.info("No reranked memories to rewrite")
            self.context.response.answer = ""
            return

        logger.info(f"Generating context from {len(memory_list)} memories")

        # Generate initial context message
        rewritten_memory = await self._generate_context_message(query, messages, memory_list)

        # Store results in context
        self.context.response.answer = rewritten_memory
        self.context.response.metadata["memory_list"] = [memory.model_dump() for memory in memory_list]

    async def _generate_context_message(self, query: str, messages: List[Message], memories: List[BaseMemory]) -> str:
        """Generate context message from retrieved memories"""
        if not memories:
            return ""

        try:
            logger.info("memories")
            # Format retrieved memories
            formatted_memories = self._format_memories_for_context(memories)

            if self.op_params.get("enable_llm_rewrite", True):
                context_content = await self._rewrite_context(query, formatted_memories, messages)
            else:
                context_content = formatted_memories

            return context_content

        except Exception as e:
            logger.error(f"Error generating context message: {e}")
            return self._format_memories_for_context(memories)

    async def _rewrite_context(self, query: str, context_content: str, messages: List[Message]) -> str:
        """LLM-based context rewriting to make experiences more relevant and actionable"""
        if not context_content:
            return context_content

        try:
            # Extract current context
            current_context = self._extract_context(messages)

            prompt = self.prompt_format(
                prompt_name="memory_rewrite_prompt",
                current_query=query,
                current_context=current_context,
                original_context=context_content)

            response = await self.llm.achat([Message(role=Role.USER, content=prompt)])

            # Extract rewritten context
            rewritten_context = self._parse_json_response(response.content, "rewritten_context")

            if rewritten_context and rewritten_context.strip():
                logger.info("Context successfully rewritten for current task")
                return rewritten_context.strip()

            return context_content

        except Exception as e:
            logger.error(f"Error in context rewriting: {e}")
            return context_content

    @staticmethod
    def _format_memories_for_context(memories: List[BaseMemory]) -> str:
        """Format memories for context generation"""
        formatted_memories = []

        for i, memory in enumerate(memories, 1):
            condition = memory.when_to_use
            memory_content = memory.content
            memory_text = f"Memory {i} :\n When to use: {condition}\n Content: {memory_content}\n"

            formatted_memories.append(memory_text)

        return "\n".join(formatted_memories)

    @staticmethod
    def _extract_context(messages: List[Message]) -> str:
        """Extract relevant context from messages"""
        if not messages:
            return ""

        context_parts = []

        # Add recent messages if available
        recent_messages = messages[-3:]  # Last 3 messages
        message_summaries = []
        for message in recent_messages:
            content = message.content[:300] + "..." if len(message.content) > 300 else message.content
            message_summaries.append(f"- {message.role.value}: {content}")

        if message_summaries:
            context_parts.append("Recent conversation:\n" + "\n".join(message_summaries))

        return "\n\n".join(context_parts)

    @staticmethod
    def _parse_json_response(response: str, key: str) -> str:
        """Parse JSON response to extract specific key"""
        try:
            # Try to extract JSON blocks
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_blocks = re.findall(json_pattern, response)

            if json_blocks:
                parsed = json.loads(json_blocks[0])
                if isinstance(parsed, dict) and key in parsed:
                    return parsed[key]

            # Fallback: try to parse the entire response as JSON
            parsed = json.loads(response)
            if isinstance(parsed, dict) and key in parsed:
                return parsed[key]

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response for key '{key}', using raw response")
            # If JSON parsing fails, return the response as-is for fallback
            return response.strip()

        return ""
