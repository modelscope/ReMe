import json
from typing import List, Dict

from loguru import logger

from flowllm import C, BaseLLMOp
from reme_ai.schema.memory import BaseMemory, TaskMemory
from reme_ai.schema.message import Message, Trajectory
from reme_ai.utils.memory_utils import merge_messages_content


@C.register_op()
class SimpleComparativeSummaryOp(BaseLLMOp):
    current_path: str = __file__

    def compare_summary_trajectory(self, trajectory_a: Trajectory, trajectory_b: Trajectory) -> List[BaseMemory]:
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

        task_id_dict: Dict[str, List[Trajectory]] = {}
        for trajectory in trajectories:
            if trajectory.task_id not in task_id_dict:
                task_id_dict[trajectory.task_id] = []
            task_id_dict[trajectory.task_id].append(trajectory)

        experience_list = []
        for task_id, task_trajectories in task_id_dict.items():
            task_trajectories: List[Trajectory] = sorted(task_trajectories, key=lambda x: x.score, reverse=True)
            if len(task_trajectories) < 2:
                continue

            if task_trajectories[0].score > task_trajectories[-1].score:
                experiences = self.compare_summary_trajectory(trajectory_a=task_trajectories[0],
                                                             trajectory_b=task_trajectories[-1])
                experience_list.extend(experiences)

        self.context.comparative_summary_experiences = experience_list
        for e in experience_list:
            logger.info(f"add experience when_to_use={e.when_to_use}\ncontent={e.content}")
