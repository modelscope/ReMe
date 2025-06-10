
# import os
# import time
# import json
# import best_logger
# import agentscope
# from experiencemaker.module.base_module import BaseModule
# from experiencemaker.schema.trajectory import Trajectory as OutputTrajectory
# from experiencemaker.schema.trajectory import Message as OutputTrajectoryMessage

# from datetime import datetime
# from pydantic import BaseModel, Field
# import uuid
# from typing import (
#     Literal,
#     Union,
#     List,
#     Optional,
#     Dict,
#     Any,
#     Sequence,
# )


# from experiencemaker.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
# from agentscope.agents import ReActAgent, DialogAgent
# from beyond.trajectory import Trajectory as TrajectoryOperation
# from beyond.solver import TaskExecutor
# from agentscope.message import Msg
# from beyond.planner import *
# from beyond.debug import *
# from best_logger import *
# from loguru import logger


# def run_agent_and_extract_memory(msg_question, traj, agent):
#     if not isinstance(msg_question, list):
#         raise ValueError("msg_question should be a list of Msg objects")
#     agent_ret = agent(msg_question)
#     latest_agent_memory_buffer = msg_sort(agent.memory.get_memory())
#     traj.add_steps(latest_agent_memory_buffer)
#     return latest_agent_memory_buffer, agent_ret

    
# def msg_sort(msg_list: List[Msg]) -> List[Msg]:
#     """
#     Sort the message list by timestamp.
#     """
#     sorted_msg = sorted(
#         msg_list,
#         key=lambda msg: datetime.strptime(msg.timestamp, "%Y-%m-%d %H:%M:%S.%f")
#     )

#     return sorted_msg


# class MainAgent(BaseAgentWrapper):
#     mcp_url: str = Field(
#         default=os.getenv('MCP_URL', 'http://localhost:33333/sse'),
#         description="The URL of the MCP server.",
#     )
    
#     def __init__(self, *args, **kwargs):
#         return super().__init__(*args, **kwargs)

#     def execute(self, query, **kwargs):
#         question = query.strip()
#         ref_answer = "not available"

#         print_dict({
#             'question': question,
#             'ref_answer': ref_answer,
#         }, mod='gaia_result')

#         try:
#         except Exception as e:
#             logger.exception(f"Error in solving task {question}: {e}")
#             raise RuntimeError(f"Error in solving task {question}: {e}")

#         print_dict({
#             'question': question,
#             'ref_answer': ref_answer,
#             'predicted_result': final_answer,
#         }, mod='gaia_result')


#         role_mapping = {
#             'system': 'system',
#             'end-user': 'user',
#             'commander': 'user',
#             'assistant': 'assistant',
#             'tool-agent': 'user',
#             'tool': 'tool',
#         }
#         output_trajectory = OutputTrajectory(
#             steps=[OutputTrajectoryMessage(
#                 role=role_mapping[step.executor],
#                 content=step.content,
#                 timestamp=step.timestamp
#             ) for step in traj.raw_steps],
#             done=True,
#             query=question,
#             answer=final_answer,
#             current_step=len(traj.raw_steps),
#         )
#         return output_trajectory

