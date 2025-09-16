import re
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.schema.message import Message
from loguru import logger

from reme_ai.schema.memory import PersonalMemory


@C.register_op()
class UpdateInsightOp(BaseAsyncOp):
    """
    This class is responsible for updating insight value in a memory system. It filters insight nodes
    based on their association with observed nodes, utilizes a ranking model to prioritize them,
    generates refreshed insights via an LLM, and manages node statuses and content updates.
    """
    file_path: str = __file__

    async def async_execute(self):
        """
        Update insight values based on new observation memories.
        
        Process:
        1. Get insight subjects and personal memories from context
        2. Find relevant observations for each insight subject
        3. Update insight values using LLM integration
        4. Store updated insights in context
        """
        # Get memories from previous operations
        insight_memories = self.context.response.metadata.get("insight_memories", [])
        personal_memories = self.context.response.metadata.get("personal_memories", [])

        if not insight_memories:
            logger.info("No insight memories to update")
            self.context.response.metadata["updated_insight_memories"] = []
            return

        if not personal_memories:
            logger.info("No observation memories available for insight updates")
            self.context.response.metadata["updated_insight_memories"] = []
            return

        # Get operation parameters
        update_insight_threshold = self.op_params.get("update_insight_threshold", 0.3)
        update_insight_max_count = self.op_params.get("update_insight_max_count", 5)
        user_name = self.context.get("user_name", "user")

        logger.info(f"Updating {len(insight_memories)} insights with {len(personal_memories)} observations")

        # Score and filter insights based on relevance to observations
        scored_insights = self._score_insights_by_relevance(
            insight_memories, personal_memories, update_insight_threshold
        )

        if not scored_insights:
            logger.info("No insights meet relevance threshold for updating")
            self.context.response.metadata["updated_insight_memories"] = []
            return

        # Select top insights for updating
        top_insights = sorted(scored_insights, key=lambda x: x[1], reverse=True)[:update_insight_max_count]
        logger.info(f"Selected {len(top_insights)} insights for updating")

        # Update each selected insight
        updated_insights = []
        for insight_memory, relevance_score, relevant_observations in top_insights:
            updated_insight = await self._update_insight_with_observations(
                insight_memory, relevant_observations, user_name
            )
            if updated_insight:
                updated_insights.append(updated_insight)

        # Store results in context
        self.context.response.metadata["updated_insight_memories"] = updated_insights
        logger.info(f"Successfully updated {len(updated_insights)} insight memories")

    def _score_insights_by_relevance(self, insight_memories: List[PersonalMemory],
                                     observation_memories: List[PersonalMemory],
                                     threshold: float) -> List[tuple]:
        """
        Score insight memories based on relevance to observation memories.
        
        Args:
            insight_memories: List of insight memories to score
            observation_memories: List of observation memories for comparison
            threshold: Minimum relevance score threshold
            
        Returns:
            List[tuple]: List of (insight_memory, relevance_score, relevant_observations)
        """
        scored_insights = []

        for insight_memory in insight_memories:
            relevant_observations = []
            max_relevance = 0.0

            insight_subject = getattr(insight_memory, 'reflection_subject', '') or insight_memory.content
            insight_keywords = set(insight_memory.content.lower().split())

            # Find observations relevant to this insight
            for obs_memory in observation_memories:
                relevance_score = self._calculate_relevance_score(
                    insight_memory, obs_memory, insight_keywords
                )

                if relevance_score >= threshold:
                    relevant_observations.append(obs_memory)
                    max_relevance = max(max_relevance, relevance_score)

            # Include insight if it has relevant observations
            if relevant_observations:
                scored_insights.append((insight_memory, max_relevance, relevant_observations))
                logger.info(
                    f"Insight '{insight_subject[:40]}...' scored {max_relevance:.3f} with {len(relevant_observations)} observations"
                )

        return scored_insights

    @staticmethod
    def _calculate_relevance_score(insight_memory: PersonalMemory,
                                   obs_memory: PersonalMemory, insight_keywords: set) -> float:
        """Calculate relevance score between insight and observation memory"""
        # High relevance for same reflection subject
        insight_subject = getattr(insight_memory, 'reflection_subject', '')
        obs_subject = getattr(obs_memory, 'reflection_subject', '')

        if insight_subject and obs_subject and insight_subject == obs_subject:
            return 0.9

        # Medium relevance for keyword overlap
        obs_keywords = set(obs_memory.content.lower().split())
        intersection = len(insight_keywords.intersection(obs_keywords))
        union = len(insight_keywords.union(obs_keywords))

        return intersection / union if union > 0 else 0.0

    async def _update_insight_with_observations(self, insight_memory: PersonalMemory,
                                          relevant_observations: List[PersonalMemory],
                                          user_name: str) -> PersonalMemory:
        """
        Update a single insight memory based on relevant observations using LLM.
        
        Args:
            insight_memory: The insight memory to update
            relevant_observations: List of relevant observation memories
            user_name: The target username
            
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
            updated_content = UpdateInsightOp.parse_update_insight_response(response_text, self.language)

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
            updated_insight.update_time_modified()

            logger.info(f"Updated insight: {updated_content[:50]}...")
            return updated_insight

        # Use LLM chat with callback function
        try:
            return await self.llm.achat(messages=[Message(content=full_prompt)], callback_fn=parse_update_response)
        except Exception as e:
            logger.error(f"Error updating insight: {e}")
            return insight_memory

    @staticmethod
    def parse_update_insight_response(response_text: str, language: str = "en") -> str:
        """Parse update insight response to extract updated insight content"""
        # Pattern to match both Chinese and English insight formats
        # Chinese: {user_name}的资料: <信息>
        # English: {user_name}'s profile: <Information>
        if language in ["zh", "cn"]:
            pattern = r"的资料[：:]\s*<([^<>]+)>"
        else:
            pattern = r"profile[：:]\s*<([^<>]+)>"

        matches = re.findall(pattern, response_text, re.IGNORECASE | re.MULTILINE)

        if matches:
            insight_content = matches[0].strip()
            logger.info(f"Parsed insight content: {insight_content}")
            return insight_content

        # Fallback: try to find content between angle brackets
        fallback_pattern = r"<([^<>]+)>"
        fallback_matches = re.findall(fallback_pattern, response_text)
        if fallback_matches:
            # Get the last match as it's likely the final answer
            insight_content = fallback_matches[-1].strip()
            logger.info(f"Parsed insight content (fallback): {insight_content}")
            return insight_content

        logger.warning("No insight content found in response")
        return ""
