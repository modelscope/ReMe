import json
import re
from typing import List
from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import TextExperience, ExperienceMeta
from experiencemaker.schema.message import Message, Trajectory
from experiencemaker.enumeration.role import Role


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
        all_experiences = []
        for task_result in self.join_task():
            if task_result:
                all_experiences.extend(task_result)

        logger.info(f"Extracted {len(all_experiences)} failure experiences")
        
        # Add experiences to context
        existing_experiences = self.context.get_context("extracted_experiences", [])
        existing_experiences.extend(all_experiences)
        self.context.set_context("extracted_experiences", existing_experiences)

    def _extract_failure_experience_from_steps(self, steps: List[Message], trajectory: Trajectory) -> List[TextExperience]:
        """Extract experience from failed step sequences"""
        try:
            step_content = self._format_step_sequence(steps)
            context = self._get_trajectory_context(trajectory, steps)
            
            prompt = self.prompt_format(
                prompt_name="failure_step_experience_prompt",
                query=trajectory.metadata.get('query', ''),
                step_sequence=step_content,
                context=context,
                outcome="failed"
            )

            def parse_experiences(message: Message) -> List[TextExperience]:
                try:
                    experiences_data = self._parse_json_experience_response(message.content)
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
                    
                except Exception as e:
                    logger.error(f"Error parsing failure experiences: {e}")
                    return []

            return self.llm.chat(messages=[Message(content=prompt)], callback_fn=parse_experiences)

        except Exception as e:
            logger.error(f"Error extracting failure experience: {e}")
            return []

    def _format_step_sequence(self, steps: List[Message]) -> str:
        """Format step sequence to string"""
        step_content_collector = []
        
        for step in steps:
            step_index = len(step_content_collector)
            
            if step.role == Role.ASSISTANT:
                line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                if hasattr(step, 'reasoning_content') and step.reasoning_content:
                    line += f"{step.reasoning_content}\n"
                if hasattr(step, 'tool_calls') and step.tool_calls:
                    for tool_call in step.tool_calls:
                        line += f" - tool call={tool_call.name}\n   params={tool_call.arguments}\n"
                step_content_collector.append(line)
                
            elif step.role == Role.USER:
                line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                step_content_collector.append(line)
                
            elif step.role == Role.TOOL:
                line = f"### step.{step_index} role={step.role.value} tool call result=\n{step.content}\n"
                step_content_collector.append(line)

        return "\n".join(step_content_collector).strip()

    def _get_trajectory_context(self, trajectory: Trajectory, step_sequence: List[Message]) -> str:
        """Get context of step sequence within trajectory"""
        try:
            # Find position of step sequence in trajectory
            start_idx = 0
            for i, step in enumerate(trajectory.messages):
                if step == step_sequence[0]:
                    start_idx = i
                    break

            # Extract before and after context
            context_before = trajectory.messages[max(0, start_idx - 2):start_idx]
            context_after = trajectory.messages[start_idx + len(step_sequence):start_idx + len(step_sequence) + 2]

            context = f"Query: {trajectory.metadata.get('query', 'N/A')}\n"

            if context_before:
                context += "Previous steps:\n" + "\n".join([f"- {step.content[:100]}..." for step in context_before]) + "\n"

            if context_after:
                context += "Following steps:\n" + "\n".join([f"- {step.content[:100]}..." for step in context_after])

            return context
            
        except Exception as e:
            logger.error(f"Error getting trajectory context: {e}")
            return f"Query: {trajectory.metadata.get('query', 'N/A')}"

    def _parse_json_experience_response(self, response: str) -> List[dict]:
        """Parse JSON formatted experience response"""
        try:
            # Extract JSON blocks
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_blocks = re.findall(json_pattern, response)

            if json_blocks:
                parsed = json.loads(json_blocks[0])

                # Handle array format
                if isinstance(parsed, list):
                    valid_experiences = []
                    for exp_data in parsed:
                        if isinstance(exp_data, dict) and (
                                ("when_to_use" in exp_data and "experience" in exp_data) or
                                ("condition" in exp_data and "experience" in exp_data)
                        ):
                            valid_experiences.append(exp_data)
                    return valid_experiences

                # Handle single object
                elif isinstance(parsed, dict) and (
                        ("when_to_use" in parsed and "experience" in parsed) or
                        ("condition" in parsed and "experience" in parsed)
                ):
                    return [parsed]

            # Fallback: try to parse entire response
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON experience response: {e}")

        return []