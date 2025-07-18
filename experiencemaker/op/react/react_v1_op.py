import datetime
import time
from typing import List, Dict

from loguru import logger

from experiencemaker.enumeration.role import Role
from experiencemaker.op import OP_REGISTRY
from experiencemaker.op.base_op import BaseOp
from experiencemaker.schema.message import Message
from experiencemaker.schema.request import AgentRequest
from experiencemaker.schema.response import AgentResponse
from experiencemaker.tool import TOOL_REGISTRY
from experiencemaker.tool.base_tool import BaseTool


@OP_REGISTRY.register()
class ReactV1Op(BaseOp):
    current_path: str = __file__

    def execute(self):
        request: AgentRequest = self.context.request
        response: AgentResponse = self.context.response

        max_steps: int = int(self.op_params.get("max_steps", 10))
        tool_names = self.op_params.get("tool_names", "code_tool,dashscope_search_tool")
        tools: List[BaseTool] = [TOOL_REGISTRY[x.strip()]() for x in tool_names.split(",") if x]
        tool_dict: Dict[str, BaseTool] = {x.name: x for x in tools}
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        system_prompt = self.prompt_format(prompt_name="role_prompt",
                                           time=now_time,
                                           tools=",".join([x.name for x in tools]))
        logger.info(f"system_prompt={system_prompt}")

        messages: List[Message] = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=request.query)
        ]

        for i in range(max_steps):
            assistant_message: Message = self.llm.chat(messages, tools=tools)
            messages.append(assistant_message)
            logger.info(f"assistant.{i}.content={assistant_message.content}")

            if not assistant_message.tool_calls:
                break

            for j, tool_call in enumerate(assistant_message.tool_calls):
                logger.info(f"submit step={i} tool_calls.name={tool_call.name} argument_dict={tool_call.argument_dict}")

                if tool_call.name not in tool_dict:
                    continue

                self.submit_task(tool_dict[tool_call.name].execute, **tool_call.argument_dict)
                time.sleep(1)

            for tool_result, tool_call in zip(self.join_task(), assistant_message.tool_calls):
                logger.info(f"submit step={i} tool_calls.name={tool_call.name} tool_result={tool_result}")

                assert isinstance(tool_result, str)
                tool_message = Message(role=Role.TOOL, content=tool_result, tool_call_id=tool_call.id)
                messages.append(tool_message)

        response.messages = messages
        response.answer = response.messages[-1].content
