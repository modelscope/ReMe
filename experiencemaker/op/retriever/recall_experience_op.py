from typing import List
from loguru import logger
from pydantic import Field

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.message import Message
from experiencemaker.schema.vector_node import VectorNode
from experiencemaker.schema.request import RetrieverRequest


@OP_REGISTRY.register()
class RecallExperienceOp(BaseOp):
    """
    Recall relevant experiences from vector store based on query
    """
    current_path: str = __file__

    # Configuration parameters

    def execute(self):
        """Execute recall operation"""
        request: RetrieverRequest = self.context.request
        retrieve_top_k = self.op_params.get("retrieve_top_k",15)
        query_enhancement = self.op_params.get("query_enhancement",False)
        logger.info(request)

        # Extract query and messages from request
        query = getattr(request, 'query', None)
        messages = getattr(request, 'messages', None)

        # Store in context for downstream ops
        self.context.set_context("query", request.query)
        self.context.set_context("messages", request.messages)

        try:
            # Build retrieval query
            retrieval_query = self._build_retrieve_query(query, messages, query_enhancement)
            logger.info(f"Built retrieval query: {retrieval_query}")

            # Retrieve experiences from vector store
            recalled_experiences = self._retrieve_experiences(request.workspace_id, retrieval_query, retrieve_top_k)

            logger.info(f"Recalled {len(recalled_experiences)} experiences")

            # Store results in context for downstream ops
            self.context.set_context("recalled_experiences", recalled_experiences)
            self.context.set_context("retrieval_query", retrieval_query)

        except Exception as e:
            logger.error(f"Error in recall operation: {e}")
            self.context.set_context("recalled_experiences", [])

    def _build_retrieve_query(self, query: str, messages: List[Message] = None, query_enhancement = False) -> str:
        """Build retrieval query from query and messages"""
        # Use the original query as base
        base_query = query

        # Optionally enhance with current step context if enabled
        if query_enhancement and messages:
            current_context = self._extract_context(messages)
            if current_context:
                base_query = f"{base_query} {current_context}"

        return base_query

    def _retrieve_experiences(self, workspace_id: str, query: str, retrieve_top_k: int) -> List[VectorNode]:
        """Retrieve experiences from vector store"""
        if not query:
            logger.warning("Empty query provided for vector retrieval")
            return []

        try:
            retrieved_nodes = self.vector_store.search(
                workspace_id=workspace_id,
                query=query,
                top_k=retrieve_top_k
            )

            logger.info(f"Vector retrieval found {len(retrieved_nodes)} candidates")
            return retrieved_nodes

        except Exception as e:
            logger.exception(f"Error in vector retrieval: {e}")
            return []

    def _extract_context(self, messages: List[Message]) -> str:
        """Extract relevant context from messages for query enhancement"""
        if not messages:
            return ""

        context_parts = []

        # Add recent steps if available
        recent_messages = messages[-3:]  # Last 3 messages
        message_summaries = []
        for message in recent_messages:
            content = message.content[:200] + "..." if len(message.content) > 200 else message.content
            message_summaries.append(f"- {message.role.value}: {content}")

        if message_summaries:
            context_parts.append("Recent messages:\n" + "\n".join(message_summaries))

        return "\n\n".join(context_parts)