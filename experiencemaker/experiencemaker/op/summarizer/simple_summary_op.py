import json
from typing import List

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import TextExperience, ExperienceMeta, BaseExperience
from experiencemaker.schema.message import Message, Trajectory
from experiencemaker.schema.request import SummarizerRequest
from experiencemaker.schema.response import SummarizerResponse
from experiencemaker.utils.op_utils import merge_messages_content


@OP_REGISTRY.register()
class SimpleSummaryOp(BaseOp):
    current_path: str = __file__

    def summary_trajectory(self, trajectory: Trajectory) -> List[BaseExperience]:
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
                        experience_list.append(TextExperience(workspace_id=self.context.request.workspace_id,
                                                              when_to_use=when_to_use,
                                                              content=experience,
                                                              metadata=ExperienceMeta(author=self.llm.model_name)))

                return experience_list

            except Exception as e:
                logger.exception(f"parse content failed!\n{content}")
                raise e

        return self.llm.chat(messages=[Message(content=summary_prompt)], callback_fn=parse_content)

    def execute(self):
        request: SummarizerRequest = self.context.request
        response: SummarizerResponse = self.context.response

        for trajectory in request.traj_list:
            self.submit_task(self.summary_trajectory, trajectory=trajectory)

        response.experience_list = self.join_task()
        for e in response.experience_list:
            logger.info(f"add experience when_to_use={e.when_to_use}\ncontent={e.content}")