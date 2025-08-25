import json
import re
from typing import List
from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import TextExperience, ExperienceMeta, BaseExperience
from experiencemaker.schema.message import Message, Trajectory
from experiencemaker.enumeration.role import Role
from experiencemaker.schema.response import SummarizerResponse
from experiencemaker.utils.op_utils import merge_messages_content, parse_json_experience_response, get_trajectory_context


@OP_REGISTRY.register()
class FailureExtractionOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        """Extract experiences from failed trajectories"""
        failure_trajectories: List[Trajectory] = self.context.get_context("failure_trajectories", [])
        
        if not failure_trajectories:
            logger.info("No failure trajectories found for extraction")
            return

        logger.info(f"Extracting experiences from {len(failure_trajectories)} failed trajectories")

        # Use thread pool for parallel processing
        for trajectory in failure_trajectories:
            if hasattr(trajectory, 'segments') and trajectory.segments:
                # Process segmented step sequences
                for segment in trajectory.segments:
                    self.submit_task(self._extract_failure_experience_from_steps, 
                                   steps=segment, trajectory=trajectory)
            else:
                # Process entire trajectory
                self.submit_task(self._extract_failure_experience_from_steps, 
                               steps=trajectory.messages, trajectory=trajectory)

        # Collect all experiences
        failure_experiences = self.join_task()

        logger.info(f"Extracted {len(failure_experiences)} failure experiences")
        
        # Add experiences to context
        response: SummarizerResponse = self.context.response
        response.experience_list.extend(failure_experiences)

    def _extract_failure_experience_from_steps(self, steps: List[Message], trajectory: Trajectory) -> List[BaseExperience]:
        """Extract experience from failed step sequences"""
        step_content = merge_messages_content(steps)
        context = get_trajectory_context(trajectory, steps)

        prompt = self.prompt_format(
            prompt_name="failure_step_experience_prompt",
            query=trajectory.metadata.get('query', ''),
            step_sequence=step_content,
            context=context,
            outcome="failed"
        )

        def parse_experiences(message: Message) -> List[TextExperience]:
            experiences_data = parse_json_experience_response(message.content)
            experiences = []

            for exp_data in experiences_data:
                experience: BaseExperience = TextExperience(
                    workspace_id=self.context.request.workspace_id,
                    when_to_use=exp_data.get("when_to_use", exp_data.get("condition", "")),
                    content=exp_data.get("experience", ""),
                    metadata=ExperienceMeta(author=self.llm.model_name if hasattr(self, 'llm') else "system")
                )
                experiences.append(experience)

            return experiences

        return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_experiences)