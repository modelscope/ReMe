import datetime
from typing import List

from loguru import logger

from experiencemaker.enumeration.role import Role
from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.op.react.simple_react_context import ReactContext
from experiencemaker.schema.message import Message
from experiencemaker.schema.request import AgentRequest
from experiencemaker.schema.response import AgentResponse
from experiencemaker.tool import TOOL_REGISTRY
from experiencemaker.tool.base_tool import BaseTool


@OP_REGISTRY.register()
class SimpleReactOp(BaseOp):
    current_path: str = __file__

    def execute(self):
        request: AgentRequest = self.context.request
        response: AgentResponse = self.context.response

        max_steps: int = int(self.op_params.get("max_steps", 10))
        tool_names = self.op_params.get("tool_names", "code_tool,dashscope_search_tool,terminate_tool")
        tools: List[BaseTool] = [TOOL_REGISTRY[x.strip()]() for x in tool_names.split(",") if x]
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        context: ReactContext = ReactContext(max_steps=max_steps,
                                             query=request.query,
                                             tools=tools,
                                             now_time=now_time)

        for i in range(max_steps):
            context.current_step = i
            should_act: bool = self.think(context)

            if should_act:
                self.act(context)

            else:
                break

        response.messages = context.messages
        response.answer = response.messages[-1].content

    def think(self, context: ReactContext):
        next_prompt_flag: bool = False
        if context.current_step == 0:
            user_prompt = self.prompt_format(prompt_name="role_prompt",
                                             time=context.now_time,
                                             tools=",".join(context.tool_names),
                                             query=context.query)

        elif context.has_terminate_tool:
            user_prompt = self.prompt_format(prompt_name="final_prompt", query=context.query)
        else:
            user_prompt = self.prompt_format(prompt_name="next_prompt", query=context.query)
            next_prompt_flag = True

        user_message = Message(content=user_prompt, metadata={"next_prompt": next_prompt_flag})
        context.messages = [m for m in context.messages if not m.metadata.get("next_prompt", False)] + [user_message]
        logger.info(f"step.{context.current_step} user_prompt={user_prompt}")

        if context.has_terminate_tool:
            assistant_messages: Message = self.llm.chat(context.messages)

        else:
            assistant_messages: Message = self.llm.chat(context.messages, tools=context.tools)
            for tool in assistant_messages.tool_calls:
                if tool.name == "terminate":
                    context.has_terminate_tool = True
                    break

        context.messages.append(assistant_messages)

        assistant_content: str = assistant_messages.content + "\n\n" + assistant_messages.reasoning_content
        logger.info(f"step.{context.current_step} "
                    f"assistant_content={assistant_content} "
                    f"tool_calls={assistant_messages.tool_calls}")

        return True if assistant_messages.tool_calls else False

    def act(self, context: ReactContext):
        assistant_message = context.messages[-1]
        tool_dict = {tool.name: tool for tool in context.tools}

        tool_messages: List[Message] = []
        for tool_call in assistant_message.tool_calls:
            if tool_call.name not in tool_dict:
                continue

            tool = tool_dict[tool_call.name]
            tool_result = tool.execute(**tool_call.argument_dict)
            assert isinstance(tool_result, str)
            tool_messages.append(Message(role=Role.TOOL, content=tool_result, tool_call_id=tool_call.id))
            logger.info(f"step.{context.current_step}.{tool_call.name} content={tool_result}")

        context.messages.extend(tool_messages)
