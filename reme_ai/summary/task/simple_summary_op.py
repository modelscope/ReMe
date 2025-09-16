import json
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message as FlowMessage
from loguru import logger

from reme_ai.schema import Message, Trajectory
from reme_ai.schema.memory import BaseMemory, TaskMemory
from reme_ai.utils.op_utils import merge_messages_content


@C.register_op()
class SimpleSummaryOp(BaseAsyncOp):
    file_path: str = __file__

    async def summary_trajectory(self, trajectory: Trajectory) -> List[BaseMemory]:
        execution_process = merge_messages_content(trajectory.messages)
        success_score_threshold: float = self.op_params.get("success_score_threshold", 0.9)
        logger.info(f"success_score_threshold={success_score_threshold}")

        execution_result = "success" if trajectory.score >= success_score_threshold else "fail"
        summary_prompt = self.prompt_format(prompt_name="summary_prompt",
                                            execution_process=execution_process,
                                            execution_result=execution_result,
                                            summary_example=self.get_prompt("summary_example"))

        def parse_content(message: Message):
            content = message.content
            memory_list = []
            try:
                if "```" in content:
                    content = content.split("```")[1].strip()

                if content.startswith("json"):
                    content = content.strip("json")

                for exp_dict in json.loads(content):
                    when_to_use = exp_dict.get("when_to_use", "").strip()
                    memory = exp_dict.get("memory", "").strip()
                    if when_to_use and memory:
                        memory_list.append(TaskMemory(workspace_id=self.context.get("workspace_id", ""),
                                                      when_to_use=when_to_use,
                                                      content=memory,
                                                      author=getattr(self.llm, "model_name", "system")))

                return memory_list

            except Exception as e:
                logger.exception(f"parse content failed!\n{content}")
                raise e

        return await self.llm.achat(messages=[FlowMessage(role=Role.USER, content=summary_prompt)], callback_fn=parse_content)

    async def async_execute(self):
        trajectories: list = self.context.trajectories
        trajectories: List[Trajectory] = [Trajectory(**x) if isinstance(x, dict) else x for x in trajectories]

        memory_list: List[BaseMemory] = []
        for trajectory in trajectories:
            memories = await self.summary_trajectory(trajectory)
            if memories:
                memory_list.extend(memories)

        self.context.response.answer = json.dumps([x.model_dump() for x in memory_list])
        self.context.response.metadata["memory_list"] = memory_list
        for memory in memory_list:
            logger.info(f"add memory: when_to_use={memory.when_to_use}\ncontent={memory.content}")
