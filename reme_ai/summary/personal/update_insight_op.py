from typing import List

from flowllm import C, BaseLLMOp
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import PersonalMemory
from reme_ai.utils.op_utils import parse_update_insight_response


@C.register_op()
class UpdateInsightOp(BaseLLMOp):
    """
    This class is responsible for updating insight value in a memory system. It filters insight nodes
    based on their association with observed nodes, utilizes a ranking model to prioritize them,
    generates refreshed insights via an LLM, and manages node statuses and content updates.
    """
    file_path: str = __file__

    def execute(self):
        """
        Executes the main routine of the UpdateInsightOp. This involves filtering and updating insight nodes
        based on their association with observed nodes.
        """
        # Get insight memories from context
        insight_memories: List[PersonalMemory] = self.context.response.metadata.get("insight_memories", [])
        observation_memories: List[PersonalMemory] = self.context.response.metadata.get("observation_memories", [])

        if not insight_memories:
            logger.warning("insight_memories is empty, stopping processing.")
            return

        if not observation_memories:
            logger.warning("observation_memories is empty, stopping processing.")
            return

        # Get operation parameters
        update_insight_threshold: float = self.op_params.get("update_insight_threshold", 0.1)
        update_insight_max_count: int = self.op_params.get("update_insight_max_count", 5)
        user_name = self.context.get("user_name", "user")

        logger.info(
            f"Processing {len(insight_memories)} insight memories with {len(observation_memories)} observations")

        # Filter and score insight memories based on relevance to observations
        scored_insights = self._filter_and_score_insights(insight_memories, observation_memories,
                                                          update_insight_threshold, user_name)

        if not scored_insights:
            logger.warning("No relevant insights found after filtering")
            return

        # Select top insights to update
        top_insights = sorted(scored_insights, key=lambda x: x[1], reverse=True)[:update_insight_max_count]
        logger.info(f"Selected {len(top_insights)} insights for updating")

        # Update each selected insight
        updated_insights = []
        for insight_memory, score, relevant_observations in top_insights:
            updated_insight = self._update_single_insight(insight_memory, relevant_observations, user_name)
            if updated_insight:
                updated_insights.append(updated_insight)

        # Store updated insights in context
        self.context.response.metadata["updated_insight_memories"] = updated_insights
        logger.info(f"Successfully updated {len(updated_insights)} insight memories")

    def _filter_and_score_insights(self, insight_memories: List[PersonalMemory],
                                   observation_memories: List[PersonalMemory],
                                   threshold: float, user_name: str) -> List[tuple]:
        """
        Filter and score insight memories based on their relevance to observation memories.
        
        Returns:
            List[tuple]: List of (insight_memory, max_score, relevant_observations)
        """
        scored_insights = []

        for insight_memory in insight_memories:
            # For each insight, find observations that are relevant to the same subject
            relevant_observations = []
            max_score = 0.0

            insight_subject = insight_memory.reflection_subject or ""
            insight_keywords = set(insight_memory.content.lower().split())

            for obs_memory in observation_memories:
                score = 0.0

                # If both have the same reflection subject, they're highly relevant
                if (insight_subject and
                        hasattr(obs_memory, 'reflection_subject') and
                        obs_memory.reflection_subject == insight_subject):
                    score = 0.8
                else:
                    # Otherwise, use keyword-based similarity
                    obs_keywords = set(obs_memory.content.lower().split())
                    intersection = len(insight_keywords.intersection(obs_keywords))
                    union = len(insight_keywords.union(obs_keywords))
                    score = intersection / union if union > 0 else 0.0

                if score >= threshold:
                    relevant_observations.append(obs_memory)
                    max_score = max(max_score, score)

            if relevant_observations:
                scored_insights.append((insight_memory, max_score, relevant_observations))
                logger.info(
                    f"Insight '{insight_memory.content[:50]}...' (subject: {insight_subject}) scored {max_score:.3f} with {len(relevant_observations)} relevant observations")

        return scored_insights

    def _update_single_insight(self, insight_memory: PersonalMemory,
                               relevant_observations: List[PersonalMemory],
                               user_name: str) -> PersonalMemory:
        """
        Update a single insight memory based on relevant observations using LLM.
        
        Args:
            insight_memory: The insight memory to update
            relevant_observations: List of relevant observation memories
            user_name: The target user name
            
        Returns:
            PersonalMemory: Updated insight memory or None if update failed
        """
        logger.info(
            f"Updating insight: {insight_memory.content[:50]}... with {len(relevant_observations)} observations")

        # Build observation context
        observation_texts = [obs.content for obs in relevant_observations]

        # Create prompt using the prompt format method
        insight_key = insight_memory.reflection_subject or "personal_info"
        insight_key_value = f"{insight_key}: {insight_memory.content}"

        system_prompt = self.prompt_format(prompt_name="update_insight_system", user_name=user_name)
        few_shot = self.prompt_format(prompt_name="update_insight_few_shot", user_name=user_name)
        user_query = self.prompt_format(prompt_name="update_insight_user_query",
                                        user_query="\n".join(observation_texts),
                                        insight_key=insight_key,
                                        insight_key_value=insight_key_value)

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n{user_query}"
        logger.info(f"update_insight_prompt={full_prompt}")

        def parse_update_response(message: Message) -> PersonalMemory:
            """Parse LLM response and create updated insight memory"""
            response_text = message.content
            logger.info(f"update_insight_response={response_text}")

            # Parse the response to extract updated insight
            updated_content = parse_update_insight_response(response_text, self.language)

            if not updated_content or updated_content.lower() in ['无', 'none', '']:
                logger.info(f"No update needed for insight: {insight_memory.content[:50]}...")
                return insight_memory

            if updated_content == insight_memory.content:
                logger.info(f"Insight content unchanged: {insight_memory.content[:50]}...")
                return insight_memory

            # Create updated insight memory
            updated_insight = PersonalMemory(
                workspace_id=insight_memory.workspace_id,
                memory_id=insight_memory.memory_id,
                memory_type="personal_insight",
                content=updated_content,
                target=insight_memory.target,
                reflection_subject=insight_memory.reflection_subject,
                author=getattr(self.llm, "model_name", "system"),
                metadata={
                    **insight_memory.metadata,
                    "updated_by": "update_insight_op",
                    "original_content": insight_memory.content,
                    "update_reason": "integrated_new_observations"
                }
            )
            updated_insight.update_modified_time()

            logger.info(f"Updated insight: {updated_content[:50]}...")
            return updated_insight

        # Use LLM chat with callback function
        try:
            return self.llm.chat(messages=[Message(content=full_prompt)], callback_fn=parse_update_response)
        except Exception as e:
            logger.error(f"Error updating insight: {e}")
            return insight_memory
