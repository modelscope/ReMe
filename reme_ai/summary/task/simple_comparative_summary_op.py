import json
from typing import List, Dict

from loguru import logger

from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.experience import TextExperience, ExperienceMeta, BaseExperience
from experiencemaker.schema.message import Message, Trajectory
from experiencemaker.schema.request import SummarizerRequest
from experiencemaker.schema.response import SummarizerResponse
from experiencemaker.utils.op_utils import merge_messages_content


@OP_REGISTRY.register()
class SimpleComparativeSummaryOp(BaseOp):
    current_path: str = __file__

    def compare_summary_trajectory(self, trajectory_a: Trajectory, trajectory_b: Trajectory) -> List[BaseExperience]:
        summary_prompt = self.prompt_format(prompt_name="summary_prompt",
                                            execution_process_a=merge_messages_content(trajectory_a.messages),
                                            execution_process_b=merge_messages_content(trajectory_b.messages),
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

        task_id_dict: Dict[str, List[Trajectory]] = {}
        for trajectory in request.traj_list:
            if trajectory.task_id not in task_id_dict:
                task_id_dict[trajectory.task_id] = []
            task_id_dict[trajectory.task_id].append(trajectory)

        for task_id, trajectories in task_id_dict.items():
            trajectories: List[Trajectory] = sorted(trajectories, key=lambda x: x.score, reverse=True)
            if len(trajectories) < 2:
                continue

            if trajectories[0].score > trajectories[-1].score:
                self.submit_task(self.compare_summary_trajectory, trajectory_a=trajectories[0],
                                 trajectory_b=trajectories[-1])

        response.experience_list = self.join_task()
        for e in response.experience_list:
            logger.info(f"add experience when_to_use={e.when_to_use}\ncontent={e.content}")
