import json
import re
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from loguru import logger
from pydantic import Field

from experiencemaker.enumeration.role import Role
from experiencemaker.module.prompt.prompt_mixin import PromptMixin
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer, SUMMARIZER_REGISTRY
from experiencemaker.schema.experience import Experience
from experiencemaker.schema.trajectory import Trajectory, Message


@SUMMARIZER_REGISTRY.register("step")
class StepSummarizer(BaseSummarizer, PromptMixin):
    """
    Step-level experience extractor that focuses on extracting reusable experiences
    from individual steps or step sequences in trajectories
    """

    # Feature switches - can be configured via startup parameters
    enable_step_segmentation: bool = Field(default=False, description="Enable trajectory segmentation into steps")
    enable_similar_comparison: bool = Field(default=False, description="Enable similarity search for comparison")
    enable_experience_validation: bool = Field(default=True, description="Enable experience validation")

    # LLM retries
    max_retries: int = Field(default=3, description="Maximum retries for LLM calls")

    # Concurrency control
    max_workers: int = Field(default=5, description="Maximum concurrent LLM calls")

    # Prompt configuration
    prompt_file_path: Path = Field(default=Path(__file__).parent / "step_summarizer_prompt.yaml")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create thread pool for concurrent LLM calls
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    async def _async_llm_chat(self, messages: List[Message]) -> str:
        """Async wrapper for LLM chat calls"""
        loop = asyncio.get_event_loop()

        def _sync_chat():
            response = self.llm.chat(messages)
            return response.content if response else ""

        return await loop.run_in_executor(self._executor, _sync_chat)

    async def _batch_process_with_semaphore(self, tasks, semaphore_limit: int = None):
        """Process tasks concurrently with semaphore to limit concurrent calls"""
        if semaphore_limit is None:
            semaphore_limit = self.max_workers

        semaphore = asyncio.Semaphore(semaphore_limit)

        async def _semaphore_task(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*[_semaphore_task(task) for task in tasks], return_exceptions=True)

    def _extract_experiences(self, trajectories: List[Trajectory], workspace_id: str = None,
                             **kwargs) -> List[Experience]:
        """Extract step-level experiences from trajectories (implements base class method)"""
        logger.info(f"Starting step-level experience extraction pipeline for {len(trajectories)} trajectories")

        # Run async extraction in event loop
        return asyncio.run(self._async_extract_experiences(trajectories, workspace_id, **kwargs))

    async def _async_extract_experiences(self, trajectories: List[Trajectory], workspace_id: str = None,
                                         **kwargs) -> List[Experience]:
        """Async version of experience extraction"""
        all_experiences = []

        # Classify trajectories based on trajectory.done
        success_trajectories = [traj for traj in trajectories if traj.done]
        failure_trajectories = [traj for traj in trajectories if not traj.done]

        # Process success and failure samples concurrently
        tasks = []

        if success_trajectories:
            tasks.append(
                self._async_extract_step_experiences_from_success(success_trajectories, workspace_id, **kwargs))

        if failure_trajectories:
            tasks.append(
                self._async_extract_step_experiences_from_failure(failure_trajectories, workspace_id, **kwargs))

        # Comparative analysis (if similarity search is enabled)
        if success_trajectories and failure_trajectories and self.enable_similar_comparison:
            tasks.append(self._async_extract_step_experiences_from_comparison(
                success_trajectories, failure_trajectories, workspace_id, **kwargs
            ))

        # Wait for all extraction tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in extraction task: {result}")
            elif isinstance(result, list):
                all_experiences.extend(result)

        # Validate experiences concurrently
        if self.enable_experience_validation and all_experiences:
            validated_experiences = await self._async_validate_experiences(all_experiences, **kwargs)
        else:
            validated_experiences = all_experiences

        logger.info(f"Extracted {len(validated_experiences)} validated step experiences")
        return validated_experiences

    async def _async_extract_step_experiences_from_success(self, trajectories: List[Trajectory],
                                                           workspace_id: str, **kwargs) -> List[Experience]:
        """Async extract step-level experiences from successful samples"""
        logger.info(f"Extracting step experiences from {len(trajectories)} successful trajectories")

        # First, segment all trajectories concurrently
        segmentation_tasks = [self._async_segment_trajectory_into_steps(trajectory) for trajectory in trajectories]
        segmentation_results = await self._batch_process_with_semaphore(segmentation_tasks)

        # Collect all step sequences
        all_step_sequences = []
        trajectory_contexts = []

        for i, result in enumerate(segmentation_results):
            if isinstance(result, Exception):
                logger.error(f"Error segmenting trajectory {i}: {result}")
                continue

            step_sequences = result
            for step_seq in step_sequences:
                all_step_sequences.append(step_seq)
                trajectory_contexts.append((trajectories[i], step_seq))

        # Extract experiences from all step sequences concurrently
        extraction_tasks = []
        for step_seq, (trajectory, _) in zip(all_step_sequences, trajectory_contexts):
            task = self._async_extract_success_experience_from_step_sequence(step_seq, trajectory, workspace_id)
            extraction_tasks.append(task)

        extraction_results = await self._batch_process_with_semaphore(extraction_tasks)

        # Collect all experiences
        all_experiences = []
        for result in extraction_results:
            if isinstance(result, Exception):
                logger.error(f"Error extracting success experience: {result}")
                continue
            if result:
                all_experiences.extend(result)

        return all_experiences

    async def _async_extract_success_experience_from_step_sequence(self, step_seq: List[Message],
                                                                   trajectory: Trajectory, workspace_id: str) -> List[
        Experience]:
        """Extract experience from a single step sequence"""
        try:
            step_content_collector = []
            for step in step_seq:
                step_index = len(step_content_collector)

                if step.role is Role.ASSISTANT:
                    line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                    if hasattr(step, 'reasoning_content') and step.reasoning_content:
                        line += f"{step.reasoning_content}\n"
                    if hasattr(step, 'tool_calls') and step.tool_calls:
                        for tool_call in step.tool_calls:
                            line += f" - tool call={tool_call.name}\n   params={tool_call.arguments}\n"
                    step_content_collector.append(line)
                elif step.role is Role.USER:
                    line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                    step_content_collector.append(line)
                elif step.role is Role.TOOL:
                    line = f"### step.{step_index} role={step.role.value} tool call result=\n{step.content}\n"
                    step_content_collector.append(line)

            prompt = self.prompt_format(
                prompt_name="success_step_experience_prompt",
                query=trajectory.query,
                step_sequence="\n".join(step_content_collector).strip(),
                context=self._get_trajectory_context(trajectory, step_seq),
                outcome="successful"
            )

            return await self._async_extract_with_llm(prompt, "success", workspace_id)

        except Exception as e:
            logger.error(f"Error extracting success experience: {e}")
            return []

    async def _async_extract_step_experiences_from_failure(self, trajectories: List[Trajectory],
                                                           workspace_id: str, **kwargs) -> List[Experience]:
        """Async extract step-level experiences from failed samples"""
        logger.info(f"Extracting step experiences from {len(trajectories)} failed trajectories")

        # First, segment all trajectories concurrently
        segmentation_tasks = [self._async_segment_trajectory_into_steps(trajectory) for trajectory in trajectories]
        segmentation_results = await self._batch_process_with_semaphore(segmentation_tasks)

        # Collect all step sequences
        all_step_sequences = []
        trajectory_contexts = []

        for i, result in enumerate(segmentation_results):
            if isinstance(result, Exception):
                logger.error(f"Error segmenting trajectory {i}: {result}")
                continue

            step_sequences = result
            for step_seq in step_sequences:
                all_step_sequences.append(step_seq)
                trajectory_contexts.append((trajectories[i], step_seq))

        # Extract experiences from all step sequences concurrently
        extraction_tasks = []
        for step_seq, (trajectory, _) in zip(all_step_sequences, trajectory_contexts):
            task = self._async_extract_failure_experience_from_step_sequence(step_seq, trajectory, workspace_id)
            extraction_tasks.append(task)

        extraction_results = await self._batch_process_with_semaphore(extraction_tasks)

        # Collect all experiences
        all_experiences = []
        for result in extraction_results:
            if isinstance(result, Exception):
                logger.error(f"Error extracting failure experience: {result}")
                continue
            if result:
                all_experiences.extend(result)

        return all_experiences

    async def _async_extract_failure_experience_from_step_sequence(self, step_seq: List[Message],
                                                                   trajectory: Trajectory, workspace_id: str) -> List[
        Experience]:
        """Extract experience from a single failed step sequence"""
        try:
            step_content_collector = []
            for step in step_seq:
                step_index = len(step_content_collector)

                if step.role is Role.ASSISTANT:
                    line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                    if hasattr(step, 'reasoning_content') and step.reasoning_content:
                        line += f"{step.reasoning_content}\n"
                    if hasattr(step, 'tool_calls') and step.tool_calls:
                        for tool_call in step.tool_calls:
                            line += f" - tool call={tool_call.name}\n   params={tool_call.arguments}\n"
                    step_content_collector.append(line)
                elif step.role is Role.USER:
                    line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                    step_content_collector.append(line)
                elif step.role is Role.TOOL:
                    line = f"### step.{step_index} role={step.role.value} tool call result=\n{step.content}\n"
                    step_content_collector.append(line)

            prompt = self.prompt_format(
                prompt_name="failure_step_experience_prompt",
                query=trajectory.query,
                step_sequence="\n".join(step_content_collector).strip(),
                context=self._get_trajectory_context(trajectory, step_seq),
                outcome="failed"
            )

            return await self._async_extract_with_llm(prompt, "failure", workspace_id)

        except Exception as e:
            logger.error(f"Error extracting failure experience: {e}")
            return []

    async def _async_extract_step_experiences_from_comparison(self,
                                                              success_trajectories: List[Trajectory],
                                                              failure_trajectories: List[Trajectory],
                                                              workspace_id: str,
                                                              **kwargs) -> List[Experience]:
        """Async extract step-level experiences from comparative samples"""
        logger.info(f"Extracting comparative step experiences from {len(success_trajectories)} success "
                    f"and {len(failure_trajectories)} failure trajectories")

        # Find similar step sequences for comparison (this can remain sync as it's CPU-bound)
        similar_step_pairs = self._find_similar_step_sequences(success_trajectories, failure_trajectories)

        # Extract experiences from all similar pairs concurrently
        extraction_tasks = []
        for success_steps, failure_steps, similarity_score in similar_step_pairs:
            task = self._async_extract_comparative_experience(success_steps, failure_steps, similarity_score,
                                                              workspace_id)
            extraction_tasks.append(task)

        extraction_results = await self._batch_process_with_semaphore(extraction_tasks)

        # Collect all experiences
        all_experiences = []
        for result in extraction_results:
            if isinstance(result, Exception):
                logger.error(f"Error extracting comparative experience: {result}")
                continue
            if result:
                all_experiences.extend(result)

        return all_experiences

    async def _async_extract_comparative_experience(self, success_steps: List[Message],
                                                    failure_steps: List[Message],
                                                    similarity_score: float, workspace_id: str) -> List[Experience]:
        """Extract experience from a single comparative pair"""
        try:
            prompt = self.prompt_format(
                prompt_name="comparative_step_experience_prompt",
                success_steps=self._format_step_sequence(success_steps),
                failure_steps=self._format_step_sequence(failure_steps),
                similarity_score=similarity_score
            )

            return await self._async_extract_with_llm(prompt, "comparative", workspace_id)

        except Exception as e:
            logger.error(f"Error extracting comparative experience: {e}")
            return []

    async def _async_validate_experiences(self, experiences: List[Experience], **kwargs) -> List[Experience]:
        """Async validate the quality and validity of extracted experiences"""
        logger.info(f"Validating {len(experiences)} extracted experiences")

        # Validate all experiences concurrently
        validation_tasks = [self._async_validate_single_experience(experience) for experience in experiences]
        validation_results = await self._batch_process_with_semaphore(validation_tasks)

        validated_experiences = []
        for i, result in enumerate(validation_results):
            if isinstance(result, Exception):
                logger.error(f"Error validating experience {i}: {result}")
                continue

            if result.get("is_valid", False):
                validated_experiences.append(experiences[i])
            else:
                logger.warning(f"Experience validation failed: {result.get('reason', 'Unknown reason')}")

        logger.info(f"Validated {len(validated_experiences)} out of {len(experiences)} experiences")
        return validated_experiences

    async def _async_validate_single_experience(self, experience: Experience) -> Dict[str, Any]:
        """Async validate single experience"""
        try:
            prompt = self.prompt_format(
                prompt_name="experience_validation_prompt",
                condition=experience.experience_desc,
                experience_content=experience.experience_content,
            )

            response_content = await self._async_llm_chat([Message(role=Role.USER, content=prompt)])

            # Parse validation result
            is_valid = "valid" in response_content.lower() and "invalid" not in response_content.lower()
            score_match = re.search(r'score[:\s]*([0-9.]+)', response_content.lower())
            score = float(score_match.group(1)) if score_match else 0.5

            return {
                "is_valid": is_valid and score > 0.3,
                "score": score,
                "feedback": response_content,
                "reason": "" if is_valid else "Low validation score or marked as invalid"
            }

        except Exception as e:
            logger.error(f"Error validating experience: {e}")
            return {"is_valid": False, "score": 0.0, "feedback": "", "reason": str(e)}

    async def _async_segment_trajectory_into_steps(self, trajectory: Trajectory) -> List[List[Message]]:
        """Async segment trajectory into meaningful step sequences"""
        if not self.enable_step_segmentation:
            # If segmentation is not enabled, return the entire trajectory as one step sequence
            return [trajectory.steps]

        try:
            # Use LLM for segmentation
            trajectory_content = self._format_trajectory_content(trajectory)

            prompt = self.prompt_format(
                prompt_name="step_segmentation_prompt",
                query=trajectory.query,
                trajectory_content=trajectory_content,
                total_steps=len(trajectory.steps)
            )

            response_content = await self._async_llm_chat([Message(role=Role.USER, content=prompt)])

            # Parse segmentation points
            segment_points = self._parse_segmentation_response(response_content)

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

    async def _async_extract_with_llm(self, prompt: str, experience_type: str, workspace_id: str) -> List[Experience]:
        """Async extract experiences using LLM with JSON parsing - can return multiple experiences"""
        for attempt in range(self.max_retries):
            try:
                response_content = await self._async_llm_chat([Message(role=Role.USER, content=prompt)])

                # Parse JSON response to extract experiences
                experiences_data = self._parse_json_experience_response(response_content)

                if experiences_data:
                    experiences = []
                    for exp_data in experiences_data:
                        experience = Experience(
                            experience_workspace_id=workspace_id,
                            experience_desc=exp_data.get("condition", exp_data.get("when_to_use", "")),
                            experience_content=exp_data.get("experience", ""),
                            metadata=exp_data
                        )
                        experiences.append(experience)
                    return experiences
                else:
                    logger.warning(f"Experience extraction failed: no valid JSON experience found in response")

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for experience extraction: {e}")

        logger.error(f"Failed to extract experience after {self.max_retries} attempts")
        return []

    # ========== Helper Methods (remain mostly unchanged) ==========

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
        if not self.enable_similar_comparison:
            return []

        try:
            similar_pairs = []

            # Get step sequences from success and failure trajectories
            success_step_sequences = []
            for traj in success_trajectories:
                sequences = asyncio.run(self._async_segment_trajectory_into_steps(traj))
                success_step_sequences.extend(sequences)

            failure_step_sequences = []
            for traj in failure_trajectories:
                sequences = asyncio.run(self._async_segment_trajectory_into_steps(traj))
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

            # Get embeddings using embedding model
            success_embeddings = self.vector_store.embedding_model.get_embeddings(success_texts)
            failure_embeddings = self.vector_store.embedding_model.get_embeddings(failure_texts)

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

    def _parse_json_experience_response(self, response: str) -> List[dict]:
        """Parse JSON experience response - handles both single objects and arrays"""
        try:
            # Try to extract JSON format
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_blocks = re.findall(json_pattern, response)

            if json_blocks:
                parsed = json.loads(json_blocks[0])

                # Handle array of experiences
                if isinstance(parsed, list):
                    valid_experiences = []
                    for exp_data in parsed:
                        if isinstance(exp_data, dict) and (
                                ("condition" in exp_data and "experience" in exp_data) or
                                ("when_to_use" in exp_data and "experience" in exp_data)
                        ):
                            valid_experiences.append(exp_data)
                    return valid_experiences

                # Handle single experience object
                elif isinstance(parsed, dict) and (
                        ("condition" in parsed and "experience" in parsed) or
                        ("when_to_use" in parsed and "experience" in parsed)
                ):
                    return [parsed]

            # Fallback: try to parse the entire response as JSON
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON experience response: {e}")

        return []

    def __del__(self):
        """Cleanup thread pool executor when object is destroyed"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)