from typing import List

from pydantic import Field

from experiencemaker.module.base_module import BaseModule
from experiencemaker.module.reward_fn.base_reward_fn import BaseRewardFn
from experiencemaker.schema.reward import Reward
from experiencemaker.schema.trajectory import StateMessage, ActionMessage, ToolCall
from experiencemaker.tool.base_tool import BaseTool


class BaseEnvironment(BaseModule):
    tools: List[BaseTool] = Field(default_factory=list)
    reward_fns: List[BaseRewardFn] = Field(default_factory=list)
    current_state: StateMessage = Field(default_factory=StateMessage)
    metadata: dict = Field(default_factory=dict, description="add query / answer and etc for reward calculating!")

    def reset(self):
        self.current_state = StateMessage()
        self.metadata.clear()

    def step(self, action_msg: ActionMessage, **kwargs):
        next_state: StateMessage = self.transition(action_msg=action_msg, **kwargs)

        reward: Reward = self.calculate_reward(action_msg=action_msg, next_state=next_state, **kwargs)

        done: bool = self.is_terminated(action_msg=action_msg, next_state=next_state, reward=reward, **kwargs)

        info: dict = self.build_info(action_msg=action_msg, next_state=next_state, reward=reward, done=done, **kwargs)

        self.current_state = next_state
        return next_state, reward, done, info

    def transition(self, action_msg: ActionMessage, **kwargs) -> StateMessage:
        tool_dict = {tool.name: tool for tool in self.tools}

        new_tool_calls: List[ToolCall] = []
        for tool_call in action_msg.tool_calls:
            if tool_call.name not in tool_dict:
                continue

            new_tool_call = tool_call.model_copy(deep=True)
            tool = tool_dict[tool_call.name]
            new_tool_call.result = tool.execute(**tool_call.argument_dict)
            new_tool_calls.append(new_tool_call)

        return StateMessage(tool_calls=new_tool_calls)

    def calculate_reward(self, **kwargs) -> Reward:
        return Reward()

    def is_terminated(self, **kwargs) -> bool:
        raise NotImplementedError

    def build_info(self, **kwargs):
        return {}

    def get_tool_info(self,tool_name):
        tool_dict = {tool.name: tool for tool in self.tools}
        if tool_name in tool_dict:

            return f'tool \'{tool_name}\' description is: {tool_dict[tool_name].description}\t' + f'parameters: {str(tool_dict[tool_name].input_schema)}'
        else:
            return ''

    def get_tools_info(self):
        tool_dict = {tool.name: tool for tool in self.tools}
        return {tool_name:self.get_tool_info(tool_name=tool_name) for tool_name in tool_dict}