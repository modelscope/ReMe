import json
import re
from typing import List

from loguru import logger
from pydantic import Field, model_validator

from experiencemaker.enumeration.role import Role
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.schema.trajectory import Trajectory, ContextMessage, Message
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.es_vector_store import EsVectorStore
from experiencemaker.storage.file_vector_store import FileVectorStore


class StepContextGenerator(BaseContextGenerator):
    """
    Step-level context generator that retrieves and utilizes step-level experiences
    from the experience store to provide relevant context for agent execution
    """

    # Vector Store Configuration
    vector_store_type: str = Field(default="file_vector_store")
    vector_store_hosts: str | List[str] = Field(default="http://localhost:9200")
    vector_store_index_name: str = Field(default="step_experience_store")
    store_dir: str = Field(default="./step_experiences/")

    # Retrieval Configuration
    vector_retrieve_top_k: int = Field(default=15)
    final_top_k: int = Field(default=5)
    min_score_threshold: float = Field(default=0.3)

    # Feature Switches
    enable_llm_rerank: bool = Field(default=True)
    enable_context_rewrite: bool = Field(default=True)
    enable_score_filter: bool = Field(default=True)

    @model_validator(mode="after")
    def init_vector_store(self):
        """Initialize vector store based on configuration"""
        if self.vector_store_type == "file_vector_store":
            self.vector_store = FileVectorStore(
                embedding_model=self.embedding_model,
                index_name=self.vector_store_index_name,
                store_dir=self.store_dir
            )
        elif self.vector_store_type == "es_vector_store":
            self.vector_store = EsVectorStore(
                embedding_model=self.embedding_model,
                index_name=self.vector_store_index_name,
                hosts=self.vector_store_hosts
            )
        else:
            raise ValueError(f"Unknown vector store type: {self.vector_store_type}")

        return self

    def _build_retrieve_query(self, trajectory: Trajectory, **kwargs) -> str:
        """Build retrieval query from trajectory"""
        # Use the original query as base
        base_query = trajectory.query

        # Optionally enhance with current step context if available
        current_context = kwargs.get("current_context", "")
        if current_context:
            base_query = f"{base_query} {current_context}"

        return base_query

    def vector_retrieve(self, query: str, top_k: int = 10) -> List[VectorStoreNode]:
        """Vector similarity retrieval from experience store"""
        if not query:
            logger.warning("Empty query provided for vector retrieval")
            return []

        try:
            retrieved_nodes = self.vector_store.retrieve_by_query(
                query=query,
                top_k=top_k
            )
            logger.info(f"Vector retrieval found {len(retrieved_nodes)} candidates")
            return retrieved_nodes

        except Exception as e:
            logger.error(f"Error in vector retrieval: {e}")
            return []

    def llm_rerank(self, query: str, candidates: List[VectorStoreNode]) -> List[VectorStoreNode]:
        """LLM-based reranking of candidate experiences"""
        if not self.enable_llm_rerank or not candidates:
            return candidates

        try:
            # Format candidates for LLM evaluation
            candidates_text = self._format_candidates_for_rerank(candidates)

            prompt = self.prompt_handler.experience_rerank_prompt.format(
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
                return reranked_candidates

            return candidates

        except Exception as e:
            logger.error(f"Error in LLM reranking: {e}")
            return candidates

    def llm_rewrite_context(self, query: str, context_content: str, trajectory: Trajectory) -> str:
        """LLM-based context rewriting to make experiences more relevant and actionable for current task"""
        if not self.enable_query_rewrite or not context_content:
            return context_content

        try:
            # Extract current trajectory context
            current_context = self._extract_trajectory_context(trajectory)

            prompt = self.prompt_handler.context_rewrite_prompt.format(
                current_query=query,
                current_context=current_context,
                original_context=context_content
            )

            response = self.llm.chat([Message(role=Role.USER, content=prompt)])

            # Extract rewritten context from JSON
            rewritten_context = self._parse_json_response(response.content, "rewritten_context")

            if rewritten_context and rewritten_context.strip():
                logger.info("Context successfully rewritten for current task")
                return rewritten_context.strip()

            return context_content

        except Exception as e:
            logger.error(f"Error in context rewriting: {e}")
            return context_content

    def score_based_filter(self, experiences: List[VectorStoreNode],
                           min_score: float) -> List[VectorStoreNode]:
        """Filter experiences based on quality scores"""
        if not self.enable_score_filter:
            return experiences

        filtered_experiences = []

        for exp in experiences:
            # Get confidence score from metadata
            confidence = exp.metadata.get("confidence", 0.5)
            validation_score = exp.metadata.get("validation_score", 0.5)

            # Calculate combined score
            combined_score = (confidence + validation_score) / 2

            if combined_score >= min_score:
                filtered_experiences.append(exp)
            else:
                logger.debug(f"Filtered out experience with score {combined_score:.2f}")

        logger.info(f"Score filtering: {len(filtered_experiences)}/{len(experiences)} experiences retained")
        return filtered_experiences

    def hybrid_retrieve(self, query: str, trajectory: Trajectory, top_k: int = 5) -> List[VectorStoreNode]:
        """Hybrid retrieval strategy combining multiple approaches"""
        logger.info(f"Starting hybrid retrieval for query: '{query}'")

        # Step 1: Vector retrieval to get candidates
        candidates = self.vector_retrieve(query, self.vector_retrieve_top_k)

        if not candidates:
            logger.warning("No candidates found in vector retrieval")
            return []

        # Step 2: LLM reranking (optional)
        reranked = self.llm_rerank(query, candidates)

        # Step 3: Score-based filtering (optional)
        filtered = self.score_based_filter(reranked, self.min_score_threshold)

        # Step 4: Return top-k results
        final_results = filtered[:top_k]
        logger.info(f"Hybrid retrieval completed: {len(final_results)} experiences selected")

        return final_results

    def retrieve_by_query(self, trajectory: Trajectory, query: str, **kwargs) -> List[VectorStoreNode]:
        """Retrieve experiences by query (implements base class method)"""
        return self.hybrid_retrieve(query, trajectory, self.final_top_k)

    def generate_context_message(self,
                                 trajectory: Trajectory,
                                 nodes: List[VectorStoreNode],
                                 **kwargs) -> ContextMessage:
        """Generate context message from retrieved experiences"""
        if not nodes:
            return ContextMessage(content="")

        try:
            # Format retrieved experiences
            formatted_experiences = self._format_experiences_for_context(nodes)

            prompt = self.prompt_handler.context_generation_prompt.format(
                query=trajectory.query,
                current_step=kwargs.get("current_step", ""),
                retrieved_experiences=formatted_experiences,
                num_experiences=len(nodes)
            )

            response = self.llm.chat([Message(role=Role.USER, content=prompt)])

            # Extract generated context from JSON
            context_content = self._parse_json_response(response.content, "context")

            if not context_content:
                # Fallback to simple formatting
                context_content = self._create_context(nodes)

            return ContextMessage(content=context_content)

        except Exception as e:
            logger.error(f"Error generating context message: {e}")
            return ContextMessage(content=self._create_context(nodes))

    def build_context_messages(self, task: str, experiences: List[VectorStoreNode], trajectory: Trajectory) -> List[
        Message]:
        """Build context messages from experiences for agent consumption"""
        if not experiences:
            return []

        messages = []

        # Create initial context content with experiences
        system_content = "You have access to the following relevant experiences from previous executions:\n\n"

        for i, exp in enumerate(experiences, 1):
            condition = exp.content
            experience_content = exp.metadata.get("experience", "")
            tags = exp.metadata.get("tags", [])

            system_content += f"**Experience {i}:**\n"
            system_content += f"When to use: {condition}\n"
            system_content += f"Experience: {experience_content}\n"
            system_content += f"Tags: {', '.join(tags)}\n\n"

        system_content += "Consider these experiences when planning and executing your approach."

        # Rewrite the complete context to make it more relevant to current task
        if self.enable_context_rewrite:
            system_content = self.llm_rewrite_context(task, system_content, trajectory)

        messages.append(Message(role=Role.SYSTEM, content=system_content))

        return messages

    def get_best_experiences(self, task: str, trajectory: Trajectory, max_count: int = 3) -> List[Message]:
        """Get the best relevant experiences for a task as formatted messages"""
        experiences = self.hybrid_retrieve(task, trajectory, max_count)
        return self.build_context_messages(task, experiences, trajectory)

    def _extract_trajectory_context(self, trajectory: Trajectory) -> str:
        """Extract relevant context from trajectory for query enhancement"""
        context_parts = []

        # Add recent steps if available
        if trajectory.steps:
            recent_steps = trajectory.steps[-3:]  # Last 3 steps
            step_summaries = []
            for step in recent_steps:
                step_summary = step.content[:100] + "..." if len(step.content) > 100 else step.content
                step_summaries.append(f"- {step.role.value}: {step_summary}")

            if step_summaries:
                context_parts.append("Recent steps:\n" + "\n".join(step_summaries))

        # Add metadata if available
        if trajectory.metadata:
            relevant_metadata = {k: v for k, v in trajectory.metadata.items()
                                 if k in ["domain", "task_type", "difficulty"]}
            if relevant_metadata:
                context_parts.append(f"Task metadata: {relevant_metadata}")

        return "\n\n".join(context_parts)

    def _format_candidates_for_rerank(self, candidates: List[VectorStoreNode]) -> str:
        """Format candidates for LLM reranking"""
        formatted_candidates = []

        for i, candidate in enumerate(candidates):
            condition = candidate.content
            experience = candidate.metadata.get("experience", "")
            tags = candidate.metadata.get("tags", [])
            confidence = candidate.metadata.get("confidence", 0.5)

            candidate_text = f"Candidate {i}:\n"
            candidate_text += f"Condition: {condition}\n"
            candidate_text += f"Experience: {experience}\n"
            candidate_text += f"Tags: {', '.join(tags)}\n"
            candidate_text += f"Confidence: {confidence}\n"

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
            return [int(num) for num in numbers]

        except Exception as e:
            logger.error(f"Error parsing rerank response: {e}")
            return []

    def _format_experiences_for_context(self, experiences: List[VectorStoreNode]) -> str:
        """Format experiences for context generation"""
        formatted_experiences = []

        for i, exp in enumerate(experiences, 1):
            condition = exp.content
            experience_content = exp.metadata.get("experience", "")
            experience_type = exp.metadata.get("experience_type", "general")
            tags = exp.metadata.get("tags", [])

            exp_text = f"Experience {i} ({experience_type}):\n"
            exp_text += f"When to use: {condition}\n"
            exp_text += f"Experience: {experience_content}\n"
            exp_text += f"Tags: {', '.join(tags)}"

            formatted_experiences.append(exp_text)

        return "\n\n---\n\n".join(formatted_experiences)

    def _create_context(self, experiences: List[VectorStoreNode]) -> str:
        """Create simple context when LLM generation fails"""
        if not experiences:
            return ""

        context = "Here are some relevant experiences that might help:\n\n"

        for i, exp in enumerate(experiences, 1):
            condition = exp.content
            experience_content = exp.metadata.get("experience", "")

            context += f"{i}. **When**: {condition}\n"
            context += f"   **Experience**: {experience_content}\n\n"

        return context

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
            logger.warning(f"Failed to parse JSON response for key '{key}'")

        return ""
