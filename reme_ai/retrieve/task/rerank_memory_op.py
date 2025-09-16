import json
import re
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import BaseMemory


@C.register_op()
class RerankMemoryOp(BaseAsyncOp):
    """
    Rerank and filter recalled experiences using LLM and score-based filtering
    """
    file_path: str = __file__

    async def async_execute(self):
        """Execute rerank operation"""
        memory_list: List[BaseMemory] = self.context.response.metadata["memory_list"]
        retrieval_query: str = self.context.query
        enable_llm_rerank = self.op_params.get("enable_llm_rerank", True)
        enable_score_filter = self.op_params.get("enable_score_filter", False)
        min_score_threshold = self.op_params.get("min_score_threshold", 0.3)
        top_k = self.op_params.get("top_k", 5)

        logger.info(f"top_k: {top_k}")

        if not memory_list:
            logger.info("No recalled memory_list to rerank")
            return

        logger.info(f"Reranking {len(memory_list)} memories")

        # Step 1: LLM reranking (optional)
        if enable_llm_rerank:
            memory_list = await self._llm_rerank(retrieval_query, memory_list)
            logger.info(f"After LLM reranking: {len(memory_list)} memories")

        # Step 2: Score-based filtering (optional)
        if enable_score_filter:
            memory_list = self._score_based_filter(memory_list, min_score_threshold)
            logger.info(f"After score filtering: {len(memory_list)} memories")

        # Step 3: Return top-k results
        reranked_memories = memory_list[:top_k]
        logger.info(f"Final reranked results: {len(reranked_memories)} memories")

        # Store results in context
        self.context.response.metadata["memory_list"] = reranked_memories

    async def _llm_rerank(self, query: str, candidates: List[BaseMemory]) -> List[BaseMemory]:
        """LLM-based reranking of candidate experiences"""
        if not candidates:
            return candidates

        # Format candidates for LLM evaluation
        candidates_text = self._format_candidates_for_rerank(candidates)

        prompt = self.prompt_format(
            prompt_name="memory_rerank_prompt",
            query=query,
            candidates=candidates_text,
            num_candidates=len(candidates))

        response = await self.llm.achat([Message(role=Role.USER, content=prompt)])

        # Parse reranking results
        reranked_indices = self._parse_rerank_response(response.content)

        # Reorder candidates based on LLM ranking
        if reranked_indices:
            reranked_candidates = []
            for idx in reranked_indices:
                if 0 <= idx < len(candidates):
                    reranked_candidates.append(candidates[idx])

            # Add any remaining candidates that weren't explicitly ranked
            ranked_indices_set = set(reranked_indices)
            for i, candidate in enumerate(candidates):
                if i not in ranked_indices_set:
                    reranked_candidates.append(candidate)

            return reranked_candidates

        return candidates

    @staticmethod
    def _score_based_filter(memories: List[BaseMemory], min_score: float) -> List[BaseMemory]:
        """Filter memories based on quality scores"""
        filtered_memories = []

        for memory in memories:
            # Get confidence score from metadata
            confidence = memory.metadata.get("confidence", 0.5)
            validation_score = memory.score or 0.5

            # Calculate combined score
            combined_score = (confidence + validation_score) / 2

            if combined_score >= min_score:
                filtered_memories.append(memory)
            else:
                logger.debug(f"Filtered out memory with score {combined_score:.2f}")

        logger.info(f"Score filtering: {len(filtered_memories)}/{len(memories)} memories retained")
        return filtered_memories

    @staticmethod
    def _format_candidates_for_rerank(candidates: List[BaseMemory]) -> str:
        """Format candidates for LLM reranking"""
        formatted_candidates = []

        for i, candidate in enumerate(candidates):
            condition = candidate.when_to_use
            content = candidate.content

            candidate_text = f"Candidate {i}:\n"
            candidate_text += f"Condition: {condition}\n"
            candidate_text += f"Experience: {content}\n"

            formatted_candidates.append(candidate_text)

        return "\n---\n".join(formatted_candidates)

    @staticmethod
    def _parse_rerank_response(response: str) -> List[int]:
        """Parse LLM reranking response to extract ranked indices"""
        try:
            # Try to extract JSON format
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_blocks = re.findall(json_pattern, response)

            if json_blocks:
                parsed = json.loads(json_blocks[0])
                if isinstance(parsed, dict) and "ranked_indices" in parsed:
                    return parsed["ranked_indices"]
                elif isinstance(parsed, list):
                    return parsed

            # Try to extract numbers from text
            numbers = re.findall(r'\b\d+\b', response)
            return [int(num) for num in numbers if int(num) < 100]  # Reasonable upper bound

        except Exception as e:
            logger.error(f"Error parsing rerank response: {e}")
            return []
