import json
import re
from typing import List
from loguru import logger
from pydantic import Field

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import TextExperience
from experiencemaker.schema.message import Message
from experiencemaker.schema.vector_node import VectorNode
from experiencemaker.enumeration.role import Role
from experiencemaker.schema.response import RetrieverResponse


@OP_REGISTRY.register()
class RewriteExperienceOp(BaseOp):
    """
    Generate and rewrite context messages from reranked experiences
    """
    current_path: str = __file__

    def execute(self):
        """Execute rewrite operation"""
        reranked_experiences: List[VectorNode] = self.context.get_context("reranked_experiences", [])
        query: str = self.context.get_context("query", "")
        messages: List[Message] = self.context.get_context("messages", [])
        retrieval_query: str = self.context.get_context("retrieval_query", "")

        if not reranked_experiences:
            logger.info("No reranked experiences to rewrite")
            self.context.set_context("context_message", Message(content=""))
            return

        logger.info(f"Generating context from {len(reranked_experiences)} experiences")

        # Generate initial context message
        context_message = self._generate_context_message(query, messages, reranked_experiences, retrieval_query)

        # Store results in context
        self.context.set_context("context_message", context_message)

        response: RetrieverResponse = self.context.response
        response.experience_list = [TextExperience.from_vector_node(node) for node in reranked_experiences]
        response.experience_merged = context_message


    def _generate_context_message(self, query: str, messages: List[Message], nodes: List[VectorNode],
                                  retrieval_query: str) -> str:
        """Generate context message from retrieved experiences"""
        if not nodes:
            return ""

        try:
            # Format retrieved experiences
            formatted_experiences = self._format_experiences_for_context(nodes)

            if self.op_params.get("enable_llm_rewrite", True):
                context_content = self._rewrite_context(query, formatted_experiences, messages)
            else:
                context_content = formatted_experiences

            return context_content

        except Exception as e:
            logger.error(f"Error generating context message: {e}")
            return self._format_experiences_for_context(nodes)

    def _rewrite_context(self, query: str, context_content: str, messages: List[Message]) -> str:
        """LLM-based context rewriting to make experiences more relevant and actionable"""
        if not context_content:
            return context_content

        try:
            # Extract current context
            current_context = self._extract_context(messages)

            prompt = self.prompt_format(
                prompt_name="experience_rewrite_prompt",
                current_query=query,
                current_context=current_context,
                original_context=context_content
            )

            response = self.llm.chat([Message(role=Role.USER, content=prompt)])

            # Extract rewritten context
            rewritten_context = self._parse_json_response(response.content, "rewritten_context")

            if rewritten_context and rewritten_context.strip():
                logger.info("Context successfully rewritten for current task")
                return rewritten_context.strip()

            return context_content

        except Exception as e:
            logger.error(f"Error in context rewriting: {e}")
            return context_content

    def _format_experiences_for_context(self, experiences: List[VectorNode]) -> str:
        """Format experiences for context generation"""
        formatted_experiences = []

        for i, exp in enumerate(experiences, 1):
            condition = exp.content
            experience_content = exp.metadata.get("experience_content", "")
            exp_text = f"Experience {i} :\n When to use: {condition}\n Content: {experience_content}\n"

            formatted_experiences.append(exp_text)

        return "\n".join(formatted_experiences)

    def _extract_context(self, messages: List[Message]) -> str:
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

    def _parse_json_response(self, response: str, key: str) -> str:
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