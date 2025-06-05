import datetime

from experiencescope.module.agent_wrapper.base_agent_wrapper_v2 import BaseAgentWrapperV2
from loguru import logger

from experiencescope.module.environment.base_environment import BaseEnvironment
from experiencescope.schema.trajectory import Message, StateMessage, ContextMessage, ActionMessage


class NaiveAgentWrapper(BaseAgentWrapperV2):

    def generate_action(self,
                        state: StateMessage,
                        context_msg: ContextMessage | None,
                        env: BaseEnvironment,
                        **kwargs) -> ActionMessage:

        tool_names = [x.name for x in env.tools]
        if self.trajectory.current_step == 0:
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insight_tag: bool = True if context_msg is not None and context_msg.content else False
            user_prompt = self.prompt_handler.prompt_format(
                prompt_name="role_prompt",
                insight_tag=insight_tag,
                time=now_time,
                tools=", ".join(tool_names),
                previous_insight=context_msg.content if insight_tag else "",
                query=self.trajectory.query)
            # When using the reasoning models of Qwen3 or DeepSeek R1, it is not recommended to use system prompt.
            self.trajectory.steps.append(Message(content=user_prompt))

        elif self.trajectory.metadata.get("has_terminate_tool") is True:
            user_prompt = self.prompt_handler.final_prompt.format(query=self.trajectory.query)
            self.trajectory.steps.append(Message(content=user_prompt))

        else:
            user_prompt = self.prompt_handler.next_prompt.format(query=self.trajectory.query)
            self.trajectory.steps.append(Message(content=user_prompt))

        if self.trajectory.metadata.get("has_terminate_tool") is True:
            action_msg: ActionMessage = self.llm.chat(self.trajectory.steps)
            logger.info(f"step{self.trajectory.current_step} size={len(self.trajectory.steps)} user_prompt={user_prompt}")

        else:
            action_msg: ActionMessage = self.llm.chat(messages, tools=env.tools)
            logger.info(f"step{self.trajectory.current_step} size={len(messages)} user_prompt={user_prompt} "
                        f"tool_names={tool_names}")

            for tool in action_msg.tool_calls:
                if tool.name == "terminate":
                    self.trajectory.metadata["has_terminate_tool"] = True
                    break

        self.trajectory.add_step(action_msg)
        return action_msg


    def after_step_hook(self, action_msg: ActionMessage, next_state: StateMessage, done: bool = False, **kwargs):
        if done:
            self.trajectory.answer = action_msg.content
        else:
            self.trajectory.add_step(next_state)
