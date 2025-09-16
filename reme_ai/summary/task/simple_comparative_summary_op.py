import json
from typing import List, Dict

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message as FlowMessage
from loguru import logger

from reme_ai.schema import Message, Trajectory
from reme_ai.schema.memory import BaseMemory, TaskMemory
from reme_ai.utils.op_utils import merge_messages_content


@C.register_op()
class SimpleComparativeSummaryOp(BaseAsyncOp):
    file_path: str = __file__

    async def compare_summary_trajectory(self, trajectory_a: Trajectory, trajectory_b: Trajectory) -> List[BaseMemory]:
        summary_prompt = self.prompt_format(prompt_name="summary_prompt",
                                            execution_process_a=merge_messages_content(trajectory_a.messages),
                                            execution_process_b=merge_messages_content(trajectory_b.messages),
                                            summary_example=self.get_prompt("summary_example"))

        def parse_content(message: Message):
            content = message.content
            task_memory_list = []
            try:
                content = content.split("```")[1].strip()
                if content.startswith("json"):
                    content = content.strip("json")

                for tm_dict in json.loads(content):
                    when_to_use = tm_dict.get("when_to_use", "").strip()
                    task_memory_content = tm_dict.get("experience", "").strip()
                    if when_to_use and task_memory_content:
                        task_memory_list.append(TaskMemory(workspace_id=self.context.get("workspace_id", ""),
                                                           when_to_use=when_to_use,
                                                           content=task_memory_content,
                                                           author=getattr(self.llm, 'model_name', 'system')))

                return task_memory_list

            except Exception as e:
                logger.exception(f"parse content failed!\n{content}")
                raise e

        return await self.llm.achat(messages=[FlowMessage(role=Role.USER, content=summary_prompt)], callback_fn=parse_content)

    async def async_execute(self):
        trajectories: list = self.context.get("trajectories", [])
        trajectories: List[Trajectory] = [Trajectory(**x) if isinstance(x, dict) else x for x in trajectories]

        task_id_dict: Dict[str, List[Trajectory]] = {}
        for trajectory in trajectories:
            if trajectory.task_id not in task_id_dict:
                task_id_dict[trajectory.task_id] = []
            task_id_dict[trajectory.task_id].append(trajectory)

        memory_list = []
        for task_id, task_trajectories in task_id_dict.items():
            task_trajectories: List[Trajectory] = sorted(task_trajectories, key=lambda x: x.score, reverse=True)
            if len(task_trajectories) < 2:
                continue

            if task_trajectories[0].score > task_trajectories[-1].score:
                task_memories = await self.compare_summary_trajectory(trajectory_a=task_trajectories[0],
                                                                trajectory_b=task_trajectories[-1])
                memory_list.extend(task_memories)

        self.context.response.answer = json.dumps([x.model_dump() for x in memory_list])
        self.context.response.metadata["memory_list"] = memory_list
        for tm in memory_list:
            logger.info(f"add task memory when_to_use={tm.when_to_use}\ncontent={tm.content}")
