import json
import re
from typing import List

from flowllm import C, BaseAsyncOp
from loguru import logger

from reme_ai.schema import Message, Role
from reme_ai.schema.memory import BaseMemory


@C.register_op()
class SemanticRankOp(BaseAsyncOp):
    """
    The SemanticRankOp class processes queries by retrieving memory nodes,
    removing duplicates, ranking them based on semantic relevance using a model,
    assigning scores, sorting the nodes, and storing the ranked nodes back,
    while logging relevant information.
    """
    file_path: str = __file__

    async def async_execute(self):
        """
        Executes the primary workflow of the SemanticRankOp which includes:
        - Retrieves query and memory list from context.
        - Removes duplicate memories.
        - Ranks memories semantically using LLM.
        - Assigns scores to memories.
        - Sorts memories by score.
        - Saves the ranked memories back to context.

        If no memories are retrieved or if the ranking fails,
        appropriate warnings are logged.
        """
        # Get memory list from context - previous op guarantees this exists
        memory_list: List[BaseMemory] = self.context.response.metadata["memory_list"]
        query: str = self.context.query

        # Get parameters from op_params
        enable_ranker: bool = self.op_params.get("enable_ranker", True)
        output_memory_max_count: int = self.op_params.get("output_memory_max_count", 10)

        if not memory_list:
            logger.warning("Memory list is empty!")
            return

        logger.info(f"Semantic ranking {len(memory_list)} memories for query: {query[:100]}...")

        if not enable_ranker or len(memory_list) <= output_memory_max_count:
            # Use original scores if ranker is disabled or memory count is small
            logger.info("Skipping semantic ranking - using original scores")
        else:
            # Remove duplicates based on content
            memory_dict = {memory.content.strip(): memory for memory in memory_list if memory.content.strip()}
            memory_list = list(memory_dict.values())
            logger.info(f"After deduplication: {len(memory_list)} memories")

            # Perform semantic ranking using LLM
            ranked_memories = await self._semantic_rank_memories(query, memory_list)
            if ranked_memories:
                memory_list = ranked_memories

        # Sort by score
        memory_list = sorted(memory_list, key=lambda m: m.score, reverse=True)

        # Log top ranked memories
        logger.info(f"Semantic ranking completed for query: {query[:50]}...")
        for i, memory in enumerate(memory_list[:5]):  # Log top 5
            logger.info(f"Top {i + 1}: Score={memory.score:.3f}, Content={memory.content[:80]}...")

        # Save ranked memories back to context
        self.context.response.metadata["memory_list"] = memory_list

    async def _semantic_rank_memories(self, query: str, memories: List[BaseMemory]) -> List[BaseMemory]:
        """
        Use LLM to semantically rank memories based on relevance to the query
        """
        if not memories:
            return memories

        # Format memories for ranking
        formatted_memories = SemanticRankOp.format_memories_for_llm_ranking(memories)

        # Create prompt for semantic ranking
        prompt = f"""Given the query: "{query}"

Please rank the following memories by their semantic relevance to the query. 
Rate each memory on a scale of 0.0 to 1.0 where 1.0 is most relevant.

Memories:
{formatted_memories}

Please respond in JSON format:
{{"rankings": [{{"index": 0, "score": 0.8}}, {{"index": 1, "score": 0.6}}, ...]}}"""

        response = await self.llm.achat([Message(role=Role.USER, content=prompt)])

        if not response or not response.content:
            logger.warning("LLM ranking failed, using original order")
            return memories

        # Parse and apply ranking results
        rankings = SemanticRankOp.parse_llm_ranking_response(response.content)

        if rankings:
            applied_count = SemanticRankOp.apply_semantic_scores_to_memories(memories, rankings)
            logger.info(f"Successfully applied semantic rankings to {applied_count} memories")
        else:
            logger.warning("Failed to parse ranking results")

        return memories

    @staticmethod
    def parse_llm_ranking_response(response: str) -> List[dict]:
        """Parse LLM ranking response to extract rankings."""
        try:
            # Try to extract JSON blocks
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_blocks = re.findall(json_pattern, response)

            if json_blocks:
                parsed = json.loads(json_blocks[0])
                if isinstance(parsed, dict) and "rankings" in parsed:
                    return parsed["rankings"]

            # Fallback: try to parse the entire response as JSON
            parsed = json.loads(response)
            if isinstance(parsed, dict) and "rankings" in parsed:
                return parsed["rankings"]

        except json.JSONDecodeError:
            logger.warning("Failed to parse ranking response as JSON")

        return []

    @staticmethod
    def apply_semantic_scores_to_memories(memories: List, rankings: List[dict]) -> int:
        """Apply semantic ranking scores to memory objects."""
        applied_count = 0

        for ranking in rankings:
            idx = ranking.get("index", -1)
            score = ranking.get("score", 0.0)

            if 0 <= idx < len(memories):
                # Set score on memory object
                if hasattr(memories[idx], 'score'):
                    memories[idx].score = score
                    applied_count += 1
                else:
                    # Add score as metadata if score attribute doesn't exist
                    if not hasattr(memories[idx], 'metadata'):
                        memories[idx].metadata = {}
                    memories[idx].metadata['semantic_score'] = score
                    applied_count += 1

        return applied_count

    @staticmethod
    def format_memories_for_llm_ranking(memories: List) -> str:
        """Format memories for LLM ranking input."""
        formatted_memories = []

        for i, memory in enumerate(memories):
            memory_text = f"Memory {i}:\n"
            memory_text += f"When to use: {memory.when_to_use}\n"
            memory_text += f"Content: {memory.content}\n"
            formatted_memories.append(memory_text)

        return "\n---\n".join(formatted_memories)
