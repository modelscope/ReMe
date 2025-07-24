import json
import re
from typing import List

from loguru import logger

from experiencemaker.enumeration.role import Role
from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import BaseExperience, ExperienceMeta, TextExperience
from experiencemaker.schema.message import Message, Trajectory
from experiencemaker.schema.response import SummarizerResponse
from experiencemaker.utils.op_utils import merge_messages_content, parse_json_experience_response, get_trajectory_context

@OP_REGISTRY.register()
class SuccessExtractionOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        """Extract experiences from successful trajectories"""
        success_trajectories: List[Trajectory] = self.context.get_context("success_trajectories", [])
        
        if not success_trajectories:
            logger.info("No success trajectories found for extraction")
            return

        logger.info(f"Extracting experiences from {len(success_trajectories)} successful trajectories")

        # Use thread pool for parallel processing
        for trajectory in success_trajectories:
            if "segments" in trajectory.metadata:
                # Process segmented step sequences
                for segment in trajectory.metadata["segments"]:
                    self.submit_task(self._extract_success_experience_from_steps, steps=segment, trajectory=trajectory)
            else:
                # Process entire trajectory
                self.submit_task(self._extract_success_experience_from_steps,
                                 steps=trajectory.messages, trajectory=trajectory)

        # Collect all experiences
        success_experiences = self.join_task()

        logger.info(f"Extracted {len(success_experiences)} success experiences")
        
        # Add experiences to context
        response: SummarizerResponse = self.context.response
        response.experience_list.extend(success_experiences)

    def _extract_success_experience_from_steps(self, steps: List[Message], trajectory: Trajectory) -> List[BaseExperience]:
        """Extract experience from successful step sequences"""
        step_content = merge_messages_content(steps)
        context = get_trajectory_context(trajectory, steps)

        prompt = self.prompt_format(
            prompt_name="success_step_experience_prompt",
            query=trajectory.metadata.get('query', ''),
            step_sequence=step_content,
            context=context,
            outcome="successful"
        )

        def parse_experiences(message: Message) -> List[TextExperience]:
            experiences_data = parse_json_experience_response(message.content)
            experiences = []

            for exp_data in experiences_data:
                experience = TextExperience(
                    workspace_id=self.context.request.workspace_id,
                    when_to_use=exp_data.get("when_to_use", exp_data.get("condition", "")),
                    content=exp_data.get("experience", ""),
                    metadata=ExperienceMeta(author=self.llm.model_name if hasattr(self, 'llm') else "system")
                )
                experiences.append(experience)

            return experiences

        return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_experiences)