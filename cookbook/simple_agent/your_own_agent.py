import datetime
import json
from pathlib import Path
from typing import List

from loguru import logger
from pydantic import Field, BaseModel

from experiencemaker.utils.util_function import load_env_keys

load_env_keys("../../.env")

from experiencemaker.model import OpenAICompatibleBaseLLM
from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.module.prompt.prompt_mixin import PromptMixin
from experiencemaker.schema.trajectory import Message, ActionMessage, ToolCall, StateMessage
from experiencemaker.tool import CodeTool, DashscopeSearchTool, TerminateTool
from experiencemaker.tool.base_tool import BaseTool


class AgentContext(BaseModel):
    current_step: int = Field(default=-1)
    query: str = Field(default="")
    messages: List[Message] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    has_terminate_tool: bool = Field(default=False)


class YourOwnAgent(PromptMixin):
    llm: BaseLLM | None = Field(default=None)
    max_steps: int = Field(default=10)
    tools: List[BaseTool] = [CodeTool(), DashscopeSearchTool(), TerminateTool()]
    prompt_file_path: Path = Path(__file__).parent / "your_own_agent_prompt.yaml"
    add_reasoning_content_when_content_is_empty: bool = Field(default=True)

    def think(self, context: AgentContext):
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tool_names = [x.name for x in self.tools]

        if context.current_step == 0:
            user_prompt = self.prompt_format(prompt_name="role_prompt",
                                             time=now_time,
                                             tools=", ".join(tool_names),
                                             query=context.query)

        elif context.has_terminate_tool:
            user_prompt = self.prompt_format(prompt_name="final_prompt", query=context.query)

        else:
            user_prompt = self.prompt_format(prompt_name="next_prompt", query=context.query)

        context.messages.append(Message(content=user_prompt,
                                        add_reasoning_content_when_content_is_empty=self.add_reasoning_content_when_content_is_empty))
        logger.info(f"step.{context.current_step} user_prompt={user_prompt}")

        if context.has_terminate_tool:
            action_msg: ActionMessage = self.llm.chat(context.messages)

        else:
            action_msg: ActionMessage = self.llm.chat(context.messages, tools=self.tools)
            for tool in action_msg.tool_calls:
                if tool.name == "terminate":
                    context.has_terminate_tool = True
                    break

        action_msg.add_reasoning_content_when_content_is_empty = self.add_reasoning_content_when_content_is_empty
        context.messages.append(action_msg)
        action_msg_context: str = action_msg.content + "\n\n" + action_msg.reasoning_content
        logger.info(f"step.{context.current_step} action_msg_context={action_msg_context} "
                    f"tool_calls={action_msg.tool_calls}")
        return True if action_msg.tool_calls else False

    def act(self, context: AgentContext):
        action_msg = context.messages[-1]
        assert isinstance(action_msg, ActionMessage)

        tool_dict = {tool.name: tool for tool in self.tools}

        new_tool_calls: List[ToolCall] = []
        for tool_call in action_msg.tool_calls:
            if tool_call.name not in tool_dict:
                continue

            new_tool_call = tool_call.model_copy(deep=True)
            tool = tool_dict[tool_call.name]
            new_tool_call.result = tool.execute(**tool_call.argument_dict)
            new_tool_calls.append(new_tool_call)

        state_msg = StateMessage(tool_calls=new_tool_calls,
                                 add_reasoning_content_when_content_is_empty=self.add_reasoning_content_when_content_is_empty)
        state_msg.tool_result_to_content()
        context.messages.append(state_msg)
        logger.info(f"step.{context.current_step} state_msg_context={state_msg.content}")

    def run(self, query: str) -> List[Message]:
        context: AgentContext = AgentContext(query=query)

        for i in range(self.max_steps):
            context.current_step = i

            should_act: bool = self.think(context)
            if should_act:
                self.act(context)
            else:
                break
        return context.messages


def main():
    query = "Analyze Xiaomi Corporation."
    # query = "分析一下小米公司"

    agent = YourOwnAgent(llm=OpenAICompatibleBaseLLM(model_name="qwen3-32b", temperature=0.000001))
    messages = agent.run(query=query)
    answer = messages[-1].content
    logger.info(answer)
    with open("messages.jsonl", "w") as f:
        f.write(json.dumps([x.model_dump() for x in messages], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
