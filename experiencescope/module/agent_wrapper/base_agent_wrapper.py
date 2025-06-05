from abc import ABC
from typing import List

from loguru import logger
from pydantic import Field

from beyondagent.core.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
from beyondagent.core.module.environment.base_environment import BaseEnvironment
from beyondagent.core.schema.trajectory import Trajectory, Message, StateMessage, ActionMessage, ContextMessage


class BaseAgentWrapper(BaseAgentWrapperMixin, ABC):
    max_steps: int = Field(default=10)
    enable_exploration: bool = Field(default=False)
    trajectory: Trajectory | None = Field(default_factory=Trajectory)

    def reset(self):
        self.trajectory = Trajectory()

    def before_execute_hook(self, query: str, **kwargs):
        self.trajectory.query = query

    def after_step_hook(self, action_msg: ActionMessage, next_state: StateMessage, **kwargs):
        raise NotImplementedError

    def build_messages(self,
                       state: StateMessage,
                       context_msg: ContextMessage | None,
                       env: BaseEnvironment, **kwargs) -> List[Message]:
        raise NotImplementedError

    def explore_messages(self, messages: List[Message], **kwargs) -> List[Message]:
        raise NotImplementedError

    def action_parser(self, action_msg: ActionMessage, **kwargs) -> ActionMessage:
        return action_msg

    def generate_action(self,
                        state: StateMessage,
                        context_msg: ContextMessage | None,
                        env: BaseEnvironment,
                        **kwargs) -> ActionMessage:

        messages: List[Message] = self.build_messages(state, context_msg, env, **kwargs)
        if self.enable_exploration:
            messages = self.explore_messages(messages, **kwargs)

        action_msg: ActionMessage = self.llm.chat(messages, tools=env.tools)
        return self.action_parser(action_msg)

    def after_execute_hook(self, **kwargs):
        return self.trajectory

    def execute(self, query: str, env: BaseEnvironment = None, **kwargs) -> Trajectory:
        self.before_execute_hook(query=query, **kwargs)

        current_state = env.current_state
        for i in range(self.max_steps):
            self.trajectory.current_step = i

            # generate context
            context_msg: ContextMessage | None = None
            if self.context_generator:
                context_msg = self.context_generator.execute(trajectory=self.trajectory, **kwargs)
                if context_msg.content:
                    logger.info(f"step{i}.context_msg={context_msg.content}")

            # generate action
            action_msg = self.generate_action(state=current_state, context_msg=context_msg, env=env, **kwargs)
            logger.info(f"step{i} ====== reasoning_content ======\n{action_msg.reasoning_content}\n\n"
                        f"====== content ======\n{action_msg.content}\ntool_calls={action_msg.tool_calls}")

            # generate next state
            next_state, reward, done, info = env.step(action_msg, trajectory=self.trajectory, **kwargs)
            logger.info(f"step{i}.next_state={next_state.content} reward={reward.reward_value} done={done} info={info}")

            self.after_step_hook(step_index=i,
                                 current_state=current_state,
                                 action_msg=action_msg,
                                 reward=reward,
                                 next_state=next_state,
                                 done=done,
                                 info=info,
                                 **kwargs)

            if done:
                break

            current_state = next_state

        return self.after_execute_hook(**kwargs)
