from typing import List

from pydantic import Field

from experiencemaker.module.agent_wrapper.agent_wrapper_mixin import AgentWrapperMixin
from experiencemaker.module.environment.base_environment import BaseEnvironment
from experiencemaker.schema.trajectory import Trajectory, Message, StateMessage, ActionMessage, ContextMessage


class BaseAgentWrapper(AgentWrapperMixin):
    max_steps: int = Field(default=10)
    enable_exploration: bool = Field(default=False)
    trajectory: Trajectory | None = Field(default_factory=Trajectory)

    def reset(self):
        self.trajectory.reset()

    def after_step_hook(self, **kwargs):
        raise NotImplementedError

    def build_messages(self,
                       state: StateMessage,
                       context_msg: ContextMessage | None,
                       env: BaseEnvironment, **kwargs) -> List[Message]:
        raise NotImplementedError

    def explore_messages(self, messages: List[Message], **kwargs) -> List[Message]:
        raise NotImplementedError

    def action_parser(self, action_msg: ActionMessage) -> ActionMessage:  # noqa
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

    def execute(self, query: str, env: BaseEnvironment = None, **kwargs) -> Trajectory:
        self.trajectory.query = query
        current_state = env.current_state

        for i in range(self.max_steps):
            self.trajectory.current_step = i

            # generate context
            context_msg: ContextMessage | None = None
            if self.context_generator:
                context_msg = self.context_generator.execute(trajectory=self.trajectory, **kwargs)

            # generate action
            action_msg = self.generate_action(state=current_state, context_msg=context_msg, env=env, **kwargs)

            # generate next state
            next_state, reward, done, info = env.step(action_msg, trajectory=self.trajectory, **kwargs)

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

        return self.trajectory
