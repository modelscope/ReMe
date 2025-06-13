from pathlib import Path
from typing import List

from loguru import logger
from pydantic import Field

from experiencemaker.enumeration.role import Role
from experiencemaker.module.prompt.prompt_mixin import PromptMixin
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer, SUMMARIZER_REGISTRY
from experiencemaker.schema.experience import Experience
from experiencemaker.schema.trajectory import Trajectory, Message, ActionMessage
from experiencemaker.utils.util_function import get_html_match_content


@SUMMARIZER_REGISTRY.register("simple")
class SimpleSummarizer(BaseSummarizer, PromptMixin):
    max_retries: int = Field(default=5, description="max retries")
    prompt_file_path: Path = Path(__file__).parent / "simple_summarizer_prompt.yaml"

    def _extract_trajectory_experience(self, trajectory: Trajectory, workspace_id: str) -> Experience | None:
        step_content_collector: List[str] = []

        for step in trajectory.steps:
            step_index = len(step_content_collector)

            if step.role is Role.ASSISTANT:
                line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n{step.reasoning_content}\n"
                if step.tool_calls:
                    for tool_call in step.tool_calls:
                        line += f" - tool call={tool_call.name}\n   params={tool_call.arguments}\n"
                step_content_collector.append(line)

            elif step.role is Role.USER:
                line = f"### step.{step_index} role={step.role.value} content=\n{step.content}\n"
                step_content_collector.append(line)

            elif step.role is Role.TOOL:
                line = f"### step.{step_index} role={step.role.value} tool call result=\n{step.content}\n"
                step_content_collector.append(line)

        prompt = self.prompt_format(prompt_name="summary_prompt",
                                    query=trajectory.query,
                                    execution_process="\n".join(step_content_collector).strip(),
                                    answer=trajectory.answer)

        for i in range(self.max_retries):
            action_message: ActionMessage = self.llm.chat(messages=[Message(content=prompt)])
            experience_str = get_html_match_content(action_message.content, key="experience")
            condition_str = get_html_match_content(action_message.content, key="condition")
            if experience_str and condition_str:
                return Experience(experience_workspace_id=workspace_id,
                                  experience_role=self.llm.model_name,
                                  experience_desc=condition_str,
                                  experience_content=experience_str)
            else:
                logger.warning(f"action_message.content={action_message.content} re.search failed.")

        return None

    def _extract_experiences(self, trajectories: List[Trajectory], workspace_id: str = None,
                             **kwargs) -> List[Experience]:
        experiences: List[Experience] = []
        for trajectory in trajectories:
            experience: Experience = self._extract_trajectory_experience(trajectory, workspace_id=workspace_id)
            if experience:
                experiences.append(experience)
        return experiences
