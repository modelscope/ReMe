from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message as FlowMessage
from loguru import logger

from reme_ai.schema import Message, Trajectory
from reme_ai.schema.memory import BaseMemory, TaskMemory
from reme_ai.utils.op_utils import merge_messages_content, parse_json_experience_response, get_trajectory_context


@C.register_op()
class SuccessExtractionOp(BaseAsyncOp):
    file_path: str = __file__

    async def async_execute(self):
        """Extract task memories from successful trajectories"""
        success_trajectories: List[Trajectory] = self.context.success_trajectories

        if not success_trajectories:
            logger.info("No success trajectories found for extraction")
            return

        logger.info(f"Extracting task memories from {len(success_trajectories)} successful trajectories")

        success_task_memories = []

        # Process trajectories
        for trajectory in success_trajectories:
            if "segments" in trajectory.metadata:
                # Process segmented step sequences
                for segment in trajectory.metadata["segments"]:
                    task_memories = await self._extract_success_task_memory_from_steps(segment, trajectory)
                    success_task_memories.extend(task_memories)
            else:
                # Process entire trajectory
                task_memories = await self._extract_success_task_memory_from_steps(trajectory.messages, trajectory)
                success_task_memories.extend(task_memories)

        logger.info(f"Extracted {len(success_task_memories)} success task memories")

        # Add task memories to context
        self.context.success_task_memories = success_task_memories

    async def _extract_success_task_memory_from_steps(self, steps: List[Message], trajectory: Trajectory) -> List[BaseMemory]:
        """Extract task memory from successful step sequences"""
        step_content = merge_messages_content(steps)
        context = get_trajectory_context(trajectory, steps)

        prompt = self.prompt_format(
            prompt_name="success_step_task_memory_prompt",
            query=trajectory.metadata.get('query', ''),
            step_sequence=step_content,
            context=context,
            outcome="successful"
        )

        def parse_task_memories(message: Message) -> List[BaseMemory]:
            task_memories_data = parse_json_experience_response(message.content)
            task_memories = []

            for tm_data in task_memories_data:
                task_memory = TaskMemory(
                    workspace_id=self.context.get("workspace_id", ""),
                    when_to_use=tm_data.get("when_to_use", tm_data.get("condition", "")),
                    content=tm_data.get("experience", ""),
                    author=getattr(self.llm, 'model_name', 'system'),
                    metadata=tm_data
                )
                task_memories.append(task_memory)

            return task_memories

        return await self.llm.achat(messages=[FlowMessage(role=Role.USER, content=prompt)], callback_fn=parse_task_memories)
