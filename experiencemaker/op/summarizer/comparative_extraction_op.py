import json
import re
from typing import List, Tuple, Optional
from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import TextExperience, ExperienceMeta
from experiencemaker.schema.message import Message, Trajectory
from experiencemaker.schema.response import SummarizerResponse
from experiencemaker.utils.op_utils import merge_messages_content, parse_json_experience_response


@OP_REGISTRY.register()
class ComparativeExtractionOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        """Extract comparative experiences by comparing different scoring trajectories"""
        all_trajectories: List[Trajectory] = self.context.get_context("all_trajectories", [])
        success_trajectories: List[Trajectory] = self.context.get_context("success_trajectories", [])
        failure_trajectories: List[Trajectory] = self.context.get_context("failure_trajectories", [])

        # Soft comparison: highest score vs lowest score
        if len(all_trajectories) >= 2 and self.op_params.get("enable_soft_comparison", True):
            highest_traj, lowest_traj = self._find_highest_lowest_scoring_trajectories(all_trajectories)
            if highest_traj and lowest_traj and highest_traj.score > lowest_traj.score:
                logger.info(f"Extracting soft comparative experiences: highest ({highest_traj.score:.2f}) vs lowest ({lowest_traj.score:.2f})")
                self.submit_task(self._extract_soft_comparative_experience,
                               higher_traj=highest_traj, lower_traj=lowest_traj)

        # Hard comparison: success vs failure (if similarity search is enabled)
        if (success_trajectories and failure_trajectories and
            self.op_params.get("enable_similarity_comparison", False)):

            similar_pairs = self._find_similar_step_sequences(success_trajectories, failure_trajectories)
            logger.info(f"Found {len(similar_pairs)} similar pairs for hard comparison")

            for success_steps, failure_steps, similarity_score in similar_pairs:
                self.submit_task(self._extract_hard_comparative_experience,
                               success_steps=success_steps, failure_steps=failure_steps,
                               similarity_score=similarity_score)

        comparative_experiences = self.join_task()

        logger.info(f"Extracted {len(comparative_experiences)} comparative experiences")

        # Add experiences to context
        response: SummarizerResponse = self.context.response
        response.experience_list.extend(comparative_experiences)

    def _find_highest_lowest_scoring_trajectories(self, trajectories: List[Trajectory]) -> Tuple[Optional[Trajectory], Optional[Trajectory]]:
        """Find the highest and lowest scoring trajectories"""
        if len(trajectories) < 2:
            return None, None

        # Filter trajectories with valid scores
        valid_trajectories = [traj for traj in trajectories if traj.score is not None]

        if len(valid_trajectories) < 2:
            logger.warning("Not enough trajectories with valid scores for comparison")
            return None, None

        # Sort by score
        sorted_trajectories = sorted(valid_trajectories, key=lambda x: x.score, reverse=True)

        highest_traj = sorted_trajectories[0]
        lowest_traj = sorted_trajectories[-1]

        return highest_traj, lowest_traj

    def _get_trajectory_score(self, trajectory: Trajectory) -> Optional[float]:
        """Get trajectory score"""
        return trajectory.score

    def _extract_soft_comparative_experience(self, higher_traj: Trajectory, lower_traj: Trajectory) -> List[TextExperience]:
        """Extract soft comparative experience (high score vs low score)"""
        higher_steps = self._get_trajectory_steps(higher_traj)
        lower_steps = self._get_trajectory_steps(lower_traj)
        higher_score = self._get_trajectory_score(higher_traj)
        lower_score = self._get_trajectory_score(lower_traj)

        prompt = self.prompt_format(
            prompt_name="soft_comparative_step_experience_prompt",
            higher_steps=merge_messages_content(higher_steps),
            lower_steps=merge_messages_content(lower_steps),
            higher_score=f"{higher_score:.2f}",
            lower_score=f"{lower_score:.2f}"
        )

        def parse_experiences(message: Message) -> List[TextExperience]:
            experiences_data = parse_json_experience_response(message.content)
            experiences = []

            for exp_data in experiences_data:
                experience = TextExperience(
                    workspace_id=self.context.request.workspace_id,
                    when_to_use=exp_data.get("when_to_use", exp_data.get("condition", "")),
                    content=exp_data.get("experience", ""),
                    metadata=exp_data
                )
                experiences.append(experience)

            return experiences

        return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_experiences)


    def _extract_hard_comparative_experience(self, success_steps: List[Message],
                                           failure_steps: List[Message], similarity_score: float) -> List[TextExperience]:
        """Extract hard comparative experience (success vs failure)"""
        prompt = self.prompt_format(
            prompt_name="comparative_step_experience_prompt",
            success_steps=merge_messages_content(success_steps),
            failure_steps=merge_messages_content(failure_steps),
            similarity_score=similarity_score
        )

        def parse_experiences(message: Message) -> List[TextExperience]:
            experiences_data = parse_json_experience_response(message.content)
            experiences = []

            for exp_data in experiences_data:
                experience = TextExperience(
                    workspace_id=self.context.request.workspace_id,
                    when_to_use=exp_data.get("when_to_use", exp_data.get("condition", "")),
                    content=exp_data.get("experience", ""),
                    metadata=exp_data
                )
                experiences.append(experience)


        return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_experiences)


    def _get_trajectory_steps(self, trajectory: Trajectory) -> List[Message]:
        """Get trajectory steps, prioritizing segmented steps"""
        if hasattr(trajectory, 'segments') and trajectory.segments:
            # If there are segments, merge all segments
            all_steps = []
            for segment in trajectory.segments:
                all_steps.extend(segment)
            return all_steps
        else:
            return trajectory.messages

    def _find_similar_step_sequences(self, success_trajectories: List[Trajectory],
                                   failure_trajectories: List[Trajectory]) -> List[Tuple[List[Message], List[Message], float]]:
        """Find similar step sequences for comparison"""
        if not self.op_params.get("enable_similarity_comparison", False):
            return []

        try:
            similar_pairs = []

            # Get step sequences
            success_step_sequences = []
            for traj in success_trajectories:
                if hasattr(traj, 'segments') and traj.segments:
                    success_step_sequences.extend(traj.segments)
                else:
                    success_step_sequences.append(traj.steps)

            failure_step_sequences = []
            for traj in failure_trajectories:
                if hasattr(traj, 'segments') and traj.segments:
                    failure_step_sequences.extend(traj.segments)
                else:
                    failure_step_sequences.append(traj.steps)

            # Limit comparison count to avoid computational overload
            max_sequences = self.op_params.get("max_similarity_sequences", 5)
            success_step_sequences = success_step_sequences[:max_sequences]
            failure_step_sequences = failure_step_sequences[:max_sequences]

            if not success_step_sequences or not failure_step_sequences:
                return []

            # Generate text representation for embedding
            success_texts = [merge_messages_content(seq) for seq in success_step_sequences]
            failure_texts = [merge_messages_content(seq) for seq in failure_step_sequences]

            # Get embedding vectors
            if hasattr(self, 'vector_store') and self.vector_store and hasattr(self.vector_store, 'embedding_model'):
                success_embeddings = self.vector_store.embedding_model.get_embeddings(success_texts)
                failure_embeddings = self.vector_store.embedding_model.get_embeddings(failure_texts)

                # Calculate similarity and find most similar pairs
                similarity_threshold = self.op_params.get("similarity_threshold", 0.3)

                for i, s_emb in enumerate(success_embeddings):
                    for j, f_emb in enumerate(failure_embeddings):
                        similarity = self._calculate_cosine_similarity(s_emb, f_emb)

                        if similarity > similarity_threshold:
                            similar_pairs.append((
                                success_step_sequences[i],
                                failure_step_sequences[j],
                                similarity
                            ))

                # Return top most similar pairs
                max_pairs = self.op_params.get("max_similarity_pairs", 3)
                return sorted(similar_pairs, key=lambda x: x[2], reverse=True)[:max_pairs]

        except Exception as e:
            logger.error(f"Error finding similar step sequences: {e}")

        return []

    def _calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity"""
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
