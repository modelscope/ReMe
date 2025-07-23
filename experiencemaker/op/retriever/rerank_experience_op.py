import json
import re
from typing import List
from loguru import logger
from pydantic import Field

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience
from experiencemaker.schema.message import Message
from experiencemaker.schema.vector_node import VectorNode
from experiencemaker.enumeration.role import Role
from experiencemaker.op.vector_store.recall_vector_store_op import RecallVectorStoreOp

@OP_REGISTRY.register()
class RerankExperienceOp(BaseOp):
    """
    Rerank and filter recalled experiences using LLM and score-based filtering
    """
    current_path: str = __file__

    def execute(self):

        """Execute rerank operation"""

        experiences: List[BaseExperience] = self.context.response.experience_list
        retrieval_query: str = self.context.get_context(RecallVectorStoreOp.SEARCH_QUERY, "")
        enable_llm_rerank = self.op_params.get("enable_llm_rerank", True)
        enable_score_filter = self.op_params.get("enable_score_filter", False)
        min_score_threshold = self.op_params.get("min_score_threshold", 0.3)
        top_k = self.op_params.get("top_k", 5)

        logger.info(f"top_k: {top_k}")

        if not experiences:
            logger.info("No recalled experiences to rerank")
            self.context.response.experience_list = []
            return

        try:
            logger.info(f"Reranking {len(experiences)} experiences")

            # Step 1: LLM reranking (optional)
            if enable_llm_rerank:
                experiences = self._llm_rerank(retrieval_query, experiences)
                logger.info(f"After LLM reranking: {len(experiences)} experiences")

            # Step 2: Score-based filtering (optional)
            if enable_score_filter:
                experiences = self._score_based_filter(experiences, min_score_threshold)
                logger.info(f"After score filtering: {len(experiences)} experiences")

            # Step 3: Return top-k results
            renranked_experiences = experiences[:top_k]
            logger.info(f"Final reranked results: {len(renranked_experiences)} experiences")

            # Store results in context
            self.context.response.experience_list = renranked_experiences

        except Exception as e:
            logger.error(f"Error in rerank operation: {e}")
            self.context.response.experience_list = renranked_experiences[:top_k]

    def _llm_rerank(self, query: str, candidates: List[BaseExperience]) -> List[BaseExperience]:
        """LLM-based reranking of candidate experiences"""
        if not candidates:
            return candidates

        try:
            # Format candidates for LLM evaluation
            candidates_text = self._format_candidates_for_rerank(candidates)

            prompt = self.prompt_format(
                prompt_name="experience_rerank_prompt",
                query=query,
                candidates=candidates_text,
                num_candidates=len(candidates)
            )

            response = self.llm.chat([Message(role=Role.USER, content=prompt)])

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

        except Exception as e:
            logger.error(f"Error in LLM reranking: {e}")
            return candidates

    def _score_based_filter(self, experiences: List[BaseExperience], min_score: float) -> List[BaseExperience]:
        """Filter experiences based on quality scores"""
        filtered_experiences = []

        for exp in experiences:
            # Get confidence score from metadata
            confidence = exp.metadata.get("confidence", 0.5)
            validation_score = exp.score

            # Calculate combined score
            combined_score = (confidence + validation_score) / 2

            if combined_score >= min_score:
                filtered_experiences.append(exp)
            else:
                logger.debug(f"Filtered out experience with score {combined_score:.2f}")

        logger.info(f"Score filtering: {len(filtered_experiences)}/{len(experiences)} experiences retained")
        return filtered_experiences

    def _format_candidates_for_rerank(self, candidates: List[BaseExperience]) -> str:
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

    def _parse_rerank_response(self, response: str) -> List[int]:
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