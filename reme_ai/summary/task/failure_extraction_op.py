import json
import re
from typing import List
from loguru import logger

from flowllm import C, BaseLLMOp
from reme_ai.schema.memory import BaseMemory, TaskMemory
from reme_ai.schema.message import Message, Trajectory
from reme_ai.utils.memory_utils import merge_messages_content, parse_json_experience_response, get_trajectory_context


@C.register_op()
class FailureExtractionOp(BaseLLMOp):
    current_path: str = __file__

    def execute(self):
        """Extract experiences from failed trajectories"""
        failure_trajectories: List[Trajectory] = self.context.get("failure_trajectories", [])
        
        if not failure_trajectories:
            logger.info("No failure trajectories found for extraction")
            return

        logger.info(f"Extracting experiences from {len(failure_trajectories)} failed trajectories")

        failure_experiences = []
        
        # Process trajectories
        for trajectory in failure_trajectories:
            if hasattr(trajectory, 'segments') and trajectory.segments:
                # Process segmented step sequences
                for segment in trajectory.segments:
                    experiences = self._extract_failure_experience_from_steps(segment, trajectory)
                    failure_experiences.extend(experiences)
            else:
                # Process entire trajectory
                experiences = self._extract_failure_experience_from_steps(trajectory.messages, trajectory)
                failure_experiences.extend(experiences)

        logger.info(f"Extracted {len(failure_experiences)} failure experiences")
        
        # Add experiences to context
        self.context.failure_experiences = failure_experiences

    def _extract_failure_experience_from_steps(self, steps: List[Message], trajectory: Trajectory) -> List[BaseMemory]:
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

        def parse_experiences(message: Message) -> List[BaseMemory]:
            experiences_data = parse_json_experience_response(message.content)
            experiences = []

            for exp_data in experiences_data:
                experience = TaskMemory(
                    workspace_id=self.context.get("workspace_id", ""),
                    when_to_use=exp_data.get("when_to_use", exp_data.get("condition", "")),
                    content=exp_data.get("experience", ""),
                    author=getattr(self.llm, 'model_name', 'system'),
                    metadata=exp_data
                )
                experiences.append(experience)

            return experiences

        return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_experiences)