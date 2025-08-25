import json
from typing import List

from loguru import logger

from flowllm import C, BaseLLMOp
from reme_ai.schema.memory import BaseMemory, TaskMemory
from reme_ai.schema.message import Message, Trajectory
from reme_ai.utils.memory_utils import merge_messages_content


@C.register_op()
class SimpleSummaryOp(BaseLLMOp):
    current_path: str = __file__

    def summary_trajectory(self, trajectory: Trajectory) -> List[BaseMemory]:
        execution_process = merge_messages_content(trajectory.messages)
        success_score_threshold: float = self.op_params.get("success_score_threshold", 0.9)
        logger.info(f"success_score_threshold={success_score_threshold}")

        execution_result = "success" if trajectory.score > success_score_threshold else "fail"
        summary_prompt = self.prompt_format(prompt_name="summary_prompt",
                                            execution_process=execution_process,
                                            execution_result=execution_result,
                                            summary_example=self.get_prompt("summary_example"))

        def parse_content(message: Message):
            content = message.content
            experience_list = []
            try:
                content = content.split("```")[1].strip()
                if content.startswith("json"):
                    content = content.strip("json")

                for exp_dict in json.loads(content):
                    when_to_use = exp_dict.get("when_to_use", "").strip()
                    experience = exp_dict.get("experience", "").strip()
                    if when_to_use and experience:
                        experience_list.append(TaskMemory(workspace_id=self.context.get("workspace_id", ""),
                                                              when_to_use=when_to_use,
                                                              content=experience,
                                                              author=getattr(self.llm, 'model_name', 'system')))

                return experience_list

            except Exception as e:
                logger.exception(f"parse content failed!\n{content}")
                raise e

        return self.llm.chat(messages=[Message(content=summary_prompt)], callback_fn=parse_content)

    def execute(self):
        trajectories: List[Trajectory] = self.context.get("trajectories", [])

        experience_list = []
        for trajectory in trajectories:
            experiences = self.summary_trajectory(trajectory)
            experience_list.extend(experiences)

        self.context.summary_experiences = experience_list
        for e in experience_list:
            logger.info(f"add experience when_to_use={e.when_to_use}\ncontent={e.content}")