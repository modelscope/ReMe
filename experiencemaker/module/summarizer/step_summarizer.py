import re
import uuid
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from pydantic import Field, model_validator

from experiencemaker.enumeration.role import Role
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from experiencemaker.schema.trajectory import Trajectory, Sample, SummaryMessage, Message
from experiencemaker.schema.vector_store_node import VectorStoreNode
from experiencemaker.storage.es_vector_store import EsVectorStore
from experiencemaker.storage.file_vector_store import FileVectorStore


class StepSummarizer(BaseSummarizer):
    """
    Step-level experience extractor that focuses on extracting reusable experiences
    from individual steps or step sequences in trajectories
    """

    # Vector Store 配置
    vector_store_type: str = Field(default="file_vector_store")
    vector_store_hosts: str | List[str] = Field(default="http://localhost:9200")
    vector_store_index_name: str = Field(default="step_experience_store")
    store_dir: str = Field(default="./step_experiences/")

    # 功能开关
    enable_step_segmentation: bool = Field(default=False)
    enable_similarity_search: bool = Field(default=False)
    enable_experience_validation: bool = Field(default=True)

    # llm retries
    max_retries: int = Field(default=3)

    @model_validator(mode="after")
    def init_vector_store(self):
        """initialize"""
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

    def extract_step_experiences_from_success(self, trajectories: List[Trajectory], **kwargs) -> List[SummaryMessage]:
        """Extract step-level experiences from successful samples"""
        logger.info(f"Extracting step experiences from {len(trajectories)} successful trajectories")

        all_experiences = []
        for trajectory in trajectories:
            step_sequences = self._segment_trajectory_into_steps(trajectory)

            for step_seq in step_sequences:
                try:
                    prompt = self.prompt_handler.success_step_experience_prompt.format(
                        query=trajectory.query,
                        step_sequence=self._format_step_sequence(step_seq),
                        context=self._get_trajectory_context(trajectory, step_seq),
                        outcome="successful"
                    )

                    experience = self._extract_with_llm(prompt, "success")
                    if experience:
                        all_experiences.extend(experience)

                except Exception as e:
                    logger.error(f"Error extracting success experience: {e}")
                    continue

        return all_experiences

    def extract_step_experiences_from_failure(self, trajectories: List[Trajectory], **kwargs) -> List[SummaryMessage]:
        """Extract step-level experiences from failed samples"""
        logger.info(f"Extracting step experiences from {len(trajectories)} failed trajectories")

        all_experiences = []
        for trajectory in trajectories:
            step_sequences = self._segment_trajectory_into_steps(trajectory)

            for step_seq in step_sequences:
                try:
                    prompt = self.prompt_handler.failure_step_experience_prompt.format(
                        query=trajectory.query,
                        step_sequence=self._format_step_sequence(step_seq),
                        context=self._get_trajectory_context(trajectory, step_seq),
                        outcome="failed"
                    )

                    experience = self._extract_with_llm(prompt, "failure")
                    if experience:
                        all_experiences.extend(experience)

                except Exception as e:
                    logger.error(f"Error extracting failure experience: {e}")
                    continue

        return all_experiences

    def extract_step_experiences_from_comparison(self,
                                                 success_trajectories: List[Trajectory],
                                                 failure_trajectories: List[Trajectory],
                                                 **kwargs) -> List[SummaryMessage]:
        """Extract step-level experiences from comparative samples"""
        logger.info(f"Extracting comparative step experiences from {len(success_trajectories)} success "
                    f"and {len(failure_trajectories)} failure trajectories")

        all_experiences = []

        # Find similar step sequences for comparison
        similar_step_pairs = self._find_similar_step_sequences(success_trajectories, failure_trajectories)

        for success_steps, failure_steps, similarity_score in similar_step_pairs:
            try:
                prompt = self.prompt_handler.comparative_step_experience_prompt.format(
                    success_steps=self._format_step_sequence(success_steps),
                    failure_steps=self._format_step_sequence(failure_steps),
                    similarity_score=similarity_score
                )

                experience = self._extract_with_llm(prompt, "comparative")
                if experience:
                    all_experiences.extend(experience)

            except Exception as e:
                logger.error(f"Error extracting comparative experience: {e}")
                continue

        return all_experiences

    def extract_step_experiences_general(self, trajectories: List[Trajectory], **kwargs) -> List[SummaryMessage]:
        """Extract general step experiences when no labels are provided"""
        logger.info(f"Extracting general step experiences from {len(trajectories)} trajectories")

        all_experiences = []

        for trajectory in trajectories:
            step_sequences = self._segment_trajectory_into_steps(trajectory)

            for step_seq in step_sequences:
                try:
                    prompt = self.prompt_handler.general_step_experience_prompt.format(
                        query=trajectory.query,
                        step_sequence=self._format_step_sequence(step_seq),
                        context=self._get_trajectory_context(trajectory, step_seq)
                    )

                    experience = self._extract_with_llm(prompt, "general")
                    if experience:
                        all_experiences.extend(experience)

                except Exception as e:
                    logger.error(f"Error extracting general experience: {e}")
                    continue

        return all_experiences

    def validate_experiences(self, experiences: List[SummaryMessage], **kwargs) -> List[SummaryMessage]:
        """Validate the quality and validity of extracted experiences"""
        if not self.enable_experience_validation:
            return experiences

        logger.info(f"Validating {len(experiences)} extracted experiences")

        validated_experiences = []

        for experience in experiences:
            try:
                validation_result = self._validate_single_experience(experience)

                if validation_result["is_valid"]:
                    # Add validation info to metadata
                    experience.metadata.update({
                        "validation_score": validation_result["score"],
                        "validation_feedback": validation_result["feedback"],
                        "validated_at": datetime.now().isoformat()
                    })
                    validated_experiences.append(experience)
                else:
                    logger.warning(f"Experience validation failed: {validation_result['reason']}")

            except Exception as e:
                logger.error(f"Error validating experience: {e}")
                continue

        logger.info(f"Validated {len(validated_experiences)} out of {len(experiences)} experiences")
        return validated_experiences

    def store_experiences(self, experiences: List[SummaryMessage], **kwargs):
        """Store experiences into vector storage"""
        if not experiences:
            logger.warning("No experiences to store")
            return

        # Deduplication
        unique_experiences = self._deduplicate_experiences(experiences)
        logger.info(f"Storing {len(unique_experiences)} unique experiences (deduplicated from {len(experiences)})")

        # Convert to storage nodes
        nodes = []
        for exp in unique_experiences:
            node = VectorStoreNode(
                content=exp.content,
                metadata={
                    **exp.metadata,
                    "stored_at": datetime.now().isoformat(),
                    "experience_type": "step_level"
                }
            )
            nodes.append(node)

        # Store to vector database
        refresh_index = kwargs.get("refresh_index", True)
        self.vector_store.insert(nodes, refresh_index=refresh_index)
        logger.info(f"Successfully stored {len(nodes)} step experiences")

    def execute(self, trajectories: List[Trajectory], **kwargs) -> List[Sample]:
        """Execute complete step-level experience extraction pipeline"""
        logger.info(f"Starting step-level experience extraction pipeline for {len(trajectories)} trajectories")

        all_experiences = []

        # Classify trajectories based on trajectory.done
        success_trajectories = [traj for traj in trajectories if traj.done]
        failure_trajectories = [traj for traj in trajectories if not traj.done]

        # Process success and failure samples separately
        if success_trajectories:
            success_experiences = self.extract_step_experiences_from_success(success_trajectories, **kwargs)
            all_experiences.extend(success_experiences)

        if failure_trajectories:
            failure_experiences = self.extract_step_experiences_from_failure(failure_trajectories, **kwargs)
            all_experiences.extend(failure_experiences)

        # Comparative analysis (if similarity search is enabled)
        if success_trajectories and failure_trajectories and self.enable_similarity_search:
            comparative_experiences = self.extract_step_experiences_from_comparison(
                success_trajectories, failure_trajectories, **kwargs
            )
            all_experiences.extend(comparative_experiences)

        # Validate experiences
        if self.enable_experience_validation:
            validated_experiences = self.validate_experiences(all_experiences, **kwargs)
        else:
            validated_experiences = all_experiences

        # Store experiences
        if validated_experiences:
            self.store_experiences(validated_experiences, **kwargs)

        # Construct return result
        return [Sample(steps=validated_experiences)]

    # ========== Helper Methods ==========

    def _segment_trajectory_into_steps(self, trajectory: Trajectory) -> List[List[Message]]:
        """Segment trajectory into meaningful step sequences"""
        if not self.enable_step_segmentation:
            # If segmentation is not enabled, return the entire trajectory as one step sequence
            return [trajectory.steps]

        try:
            # Use LLM for segmentation
            trajectory_content = self._format_trajectory_content(trajectory)

            prompt = self.prompt_handler.step_segmentation_prompt.format(
                query=trajectory.query,
                trajectory_content=trajectory_content,
                total_steps=len(trajectory.steps)
            )

            response = self.llm.chat([Message(role=Role.USER, content=prompt)])

            # Parse segmentation points
            segment_points = self._parse_segmentation_response(response.content)

            # Segment trajectory based on split points
            step_sequences = []
            start_idx = 0

            for end_idx in segment_points:
                if start_idx < end_idx <= len(trajectory.steps):
                    step_sequences.append(trajectory.steps[start_idx:end_idx])
                    start_idx = end_idx

            # Add remaining steps
            if start_idx < len(trajectory.steps):
                step_sequences.append(trajectory.steps[start_idx:])

            return step_sequences if step_sequences else [trajectory.steps]

        except Exception as e:
            logger.error(f"Error in step segmentation: {e}, falling back to whole trajectory")
            return [trajectory.steps]

    def _parse_segmentation_response(self, response: str) -> List[int]:
        """Parse segmentation response to extract split point positions"""
        segment_points = []

        # Try to extract JSON format split points
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        json_blocks = re.findall(json_pattern, response)

        if json_blocks:
            try:
                parsed = json.loads(json_blocks[0])
                if isinstance(parsed, dict) and "segment_points" in parsed:
                    segment_points = parsed["segment_points"]
                elif isinstance(parsed, list):
                    segment_points = parsed
            except json.JSONDecodeError:
                pass

        # If JSON parsing fails, try to extract numbers
        if not segment_points:
            numbers = re.findall(r'\b\d+\b', response)
            segment_points = [int(num) for num in numbers if int(num) > 0]

        return sorted(list(set(segment_points)))  # Remove duplicates and sort

    def _format_step_sequence(self, step_sequence: List[Message]) -> str:
        """Format step sequence to string"""
        formatted_steps = []
        for i, step in enumerate(step_sequence):
            step_info = f"Step {i + 1} [{step.role.value}]:"

            if hasattr(step, 'reasoning_content') and step.reasoning_content:
                step_info += f"\nReasoning: {step.reasoning_content}"

            step_info += f"\nContent: {step.content}"

            if hasattr(step, 'tool_calls') and step.tool_calls:
                for tool_call in step.tool_calls:
                    step_info += f"\nTool: {tool_call.name}({tool_call.arguments})"

            formatted_steps.append(step_info)

        return "\n\n".join(formatted_steps)

    def _get_trajectory_context(self, trajectory: Trajectory, step_sequence: List[Message]) -> str:
        """Get context of step sequence within trajectory"""
        # Find position of step sequence in trajectory
        start_idx = 0
        for i, step in enumerate(trajectory.steps):
            if step == step_sequence[0]:
                start_idx = i
                break

        # Extract before and after context
        context_before = trajectory.steps[max(0, start_idx - 2):start_idx]
        context_after = trajectory.steps[start_idx + len(step_sequence):start_idx + len(step_sequence) + 2]

        context = f"Query: {trajectory.query}\n"

        if context_before:
            context += "Previous steps:\n" + "\n".join([f"- {step.content[:100]}..." for step in context_before]) + "\n"

        if context_after:
            context += "Following steps:\n" + "\n".join([f"- {step.content[:100]}..." for step in context_after])

        return context

    def _format_trajectory_content(self, trajectory: Trajectory) -> str:
        """Format trajectory content to string"""
        content = ""
        for i, step in enumerate(trajectory.steps):
            content += f"Step {i + 1} ({step.role.value}):\n{step.content}\n\n"
        return content

    def _find_similar_step_sequences(self, success_trajectories: List[Trajectory],
                                     failure_trajectories: List[Trajectory]) -> List[Tuple]:
        """Use embedding model to find similar step sequences for comparison"""
        if not self.enable_similarity_search:
            return []

        try:
            similar_pairs = []

            # Get step sequences from success and failure trajectories
            success_step_sequences = []
            for traj in success_trajectories:
                sequences = self._segment_trajectory_into_steps(traj)
                success_step_sequences.extend(sequences)

            failure_step_sequences = []
            for traj in failure_trajectories:
                sequences = self._segment_trajectory_into_steps(traj)
                failure_step_sequences.extend(sequences)

            # Limit comparison count to avoid computation overload
            max_sequences = 5
            success_step_sequences = success_step_sequences[:max_sequences]
            failure_step_sequences = failure_step_sequences[:max_sequences]

            if not success_step_sequences or not failure_step_sequences:
                return []

            # Generate text representations of step sequences for embedding
            success_texts = [self._format_step_sequence(seq) for seq in success_step_sequences]
            failure_texts = [self._format_step_sequence(seq) for seq in failure_step_sequences]

            # Get embeddings
            success_embeddings = self.embedding_model.get_embeddings(success_texts)
            failure_embeddings = self.embedding_model.get_embeddings(failure_texts)

            # Calculate similarity and find most similar pairs
            for i, s_emb in enumerate(success_embeddings):
                for j, f_emb in enumerate(failure_embeddings):
                    similarity = self._calculate_cosine_similarity(s_emb, f_emb)

                    if similarity > 0.3:  # Similarity threshold
                        similar_pairs.append((
                            success_step_sequences[i],
                            failure_step_sequences[j],
                            similarity
                        ))

            # Return top 3 most similar pairs
            return sorted(similar_pairs, key=lambda x: x[2], reverse=True)[:3]

        except Exception as e:
            logger.error(f"Error finding similar step sequences: {e}")
            return []

    def _calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embedding vectors"""
        try:
            import numpy as np

            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
            import json

    def _extract_with_llm(self, prompt: str, experience_type: str) -> List[SummaryMessage]:
        for attempt in range(self.max_retries):
            try:
                response = self.llm.chat([Message(role=Role.USER, content=prompt)])
                experiences = self._parse_experience_response(response.content, experience_type)

                if experiences:
                    return experiences

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for experience extraction: {e}")

        logger.error(f"Failed to extract experience after {self.max_retries} attempts")
        return []

    def _parse_experience_response(self, response: str, experience_type: str) -> List[SummaryMessage]:
        """解析经验抽取响应"""
        experiences = []

        try:
            # 尝试提取JSON格式的经验
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_blocks = re.findall(json_pattern, response)

            for block in json_blocks:
                try:
                    parsed = json.loads(block)
                    if isinstance(parsed, list):
                        for exp_data in parsed:
                            experience = self._create_experience_message(exp_data, experience_type)
                            if experience:
                                experiences.append(experience)
                    else:
                        experience = self._create_experience_message(parsed, experience_type)
                        if experience:
                            experiences.append(experience)
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.error(f"Error parsing experience response: {e}")

        return experiences

    def _create_experience_message(self, exp_data: Dict[str, Any], experience_type: str) -> Optional[SummaryMessage]:
        """创建经验消息对象"""
        try:
            condition = exp_data.get("when_to_use", exp_data.get("condition", ""))
            experience_content = exp_data.get("experience", exp_data.get("tip_content", exp_data.get("tips", "")))

            if not condition or not experience_content:
                return None

            metadata = {
                "experience": experience_content,
                "experience_type": experience_type,
                "tags": exp_data.get("tags", []),
                "confidence": exp_data.get("confidence", 0.5),
                "extracted_at": datetime.now().isoformat(),
                "experience_id": str(uuid.uuid4())
            }

            return SummaryMessage(content=condition, metadata=metadata)

        except Exception as e:
            logger.error(f"Error creating experience message: {e}")
            return None

    def _validate_single_experience(self, experience: SummaryMessage) -> Dict[str, Any]:
        """验证单个经验的有效性"""
        try:
            prompt = self.prompt_handler.experience_validation_prompt.format(
                condition=experience.content,
                experience_content=experience.metadata.get("experience", ""),
                experience_type=experience.metadata.get("experience_type", ""),
                tags=experience.metadata.get("tags", [])
            )

            response = self.llm.chat([Message(role=Role.USER, content=prompt)])

            # 解析验证结果
            is_valid = "valid" in response.content.lower() and "invalid" not in response.content.lower()
            score_match = re.search(r'score[:\s]*([0-9.]+)', response.content.lower())
            score = float(score_match.group(1)) if score_match else 0.5

            return {
                "is_valid": is_valid and score > 0.3,
                "score": score,
                "feedback": response.content,
                "reason": "" if is_valid else "Low validation score or marked as invalid"
            }

        except Exception as e:
            logger.error(f"Error validating experience: {e}")
            return {"is_valid": False, "score": 0.0, "feedback": "", "reason": str(e)}

    def _deduplicate_experiences(self, experiences: List[SummaryMessage]) -> List[SummaryMessage]:
        unique_experiences = []
        seen_contents = set()

        for exp in experiences:
            content_hash = hash(exp.content)

            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_experiences.append(exp)

        return unique_experiences

    def extract_samples(self, trajectories: List[Trajectory], **kwargs) -> List[Sample]:
        experiences = self.execute(trajectories, **kwargs)
        return [Sample(steps=experiences)] if experiences else []

    def insert_into_vector_store(self, samples: List[Sample], **kwargs):
        all_experiences = []
        for sample in samples:
            all_experiences.extend(sample.steps)

        if all_experiences:
            self.store_experiences(all_experiences, **kwargs)