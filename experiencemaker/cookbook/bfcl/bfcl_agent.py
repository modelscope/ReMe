import os

os.environ["BFCL_DATA_PATH"] = "data/multiturn_data_base_val.jsonl"
os.environ["BFCL_ANSWER_PATH"] = "data/possible_answer"
from dotenv import load_dotenv

load_dotenv("../../.env")

import re
import time
import json
import ray
import warnings
import tempfile
import requests

from tqdm import tqdm
from pathlib import Path
from loguru import logger
from openai import OpenAI
from typing import Dict, List, Any

from bfcl_utils import (
    load_test_case,
    handle_user_turn,
    handle_tool_calls,
    extract_tool_schema,
    extract_single_turn_response,
    extract_multi_turn_responses,
    capture_and_print_score_files,
    create_error_response
)
from bfcl_eval.model_handler.api_inference.qwen import QwenAPIHandler
from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
    is_empty_execute_response,
)
from bfcl_eval.eval_checker.eval_runner import (
    multi_turn_runner,
    ast_file_runner,
)
from bfcl_eval.eval_checker.eval_runner_helper import record_cost_latency
from bfcl_eval.utils import (
    is_multi_turn,
    is_relevance_or_irrelevance,
    find_file_with_suffix,
    load_file,
)

@ray.remote
class BFCLAgent:
    """A minimal ReAct Agent for BFCL-v3(multi-turn) tasks."""

    def __init__(self,
                 index: int,
                 task_ids: List[str],
                 experiment_name: str,
                 data_path: str = os.getenv("BFCL_DATA_PATH"),
                 answer_path: Path = Path(os.getenv("BFCL_ANSWER_PATH")),
                 model_name: str = "qwen3-8b",
                 temperature: float = 0.9,
                 max_interactions: int = 30,
                 max_response_size: int = 2000,
                 num_runs: int = 1,
                 enable_thinking: bool = False,
                 use_experience: bool = False,              
                 use_fixed_experience: bool = True,              
                 experience_base_url: str = "http://0.0.0.0:8001/",
                 experience_workspace_id: str = "bfcl_8b_0725"):

        self.index: int = index
        self.task_ids: List[str] = task_ids
        self.categories: List[str] = [task_id.rsplit("_", 1)[0] if "_" in task_id else task_id for task_id in task_ids]
        self.experiment_name: str = experiment_name
        self.data_path: str = data_path
        self.answer_path: Path = answer_path
        self.model_name: str = model_name
        self.temperature: float = temperature
        self.max_interactions: int = max_interactions
        self.max_response_size: int = max_response_size
        self.num_runs: int = num_runs
        self.enable_thinking: bool = enable_thinking
        self.use_experience: bool = use_experience
        self.use_fixed_experience: bool = use_fixed_experience
        self.experience_base_url: str = experience_base_url
        self.experience_workspace_id: str = experience_workspace_id
        
        self.history: List[List[List[dict]]] = [[] for _ in range(num_runs)]
        self.test_entry: List[List[Dict[str, Any]]] = [[] for _ in range(num_runs)]
        self.original_test_entry: List[List[Dict[str, Any]]] = [[] for _ in range(num_runs)]
        self.tool_schema: List[List[List[dict]]] = [[] for _ in range(num_runs)]
        self.current_turn = [[0 for _ in range(len(task_ids))] for _ in range(num_runs)]
        
        for run_id in range(num_runs):
            for task_index in range(len(task_ids)):
                self.init_state(run_id, task_index)

    def init_state(self, run_id, i) -> Dict[str, Any]:
        """载入测试用例并返回首条 user 消息"""
        self.test_entry[run_id].append(load_test_case(self.data_path, self.task_ids[i]))
        self.original_test_entry[run_id].append(self.test_entry[run_id][i].get("extra", {}))
        self.tool_schema[run_id].append(extract_tool_schema(self.test_entry[run_id][i].get("tools", [{}])))

        # 初始历史
        msg = self.test_entry[run_id][i].get("messages", [])[0]
        if self.use_experience:
            query = msg["content"]
            exp = self.get_experience(query)
            self.history[run_id].append([self.get_query_with_experience(query, exp)])
        else:
            self.history[run_id].append([msg])
        self.current_turn[run_id][i] = 1

    def get_query_with_experience(self, query: str, experience: str):
        return {
            "role": "user",
            "content": "Task:\n" + query + "\n\nSome Related Experience to help you to complete the task:\n" + experience
        }
    
    def get_experience(self, query: str):
        response = requests.post(url=self.experience_base_url + "retriever", json={
            "workspace_id": self.experience_workspace_id,
            "query": query,
            "top_k": 5
        })
        logger.info(f"query:{query}")

        if response.status_code != 200:
            print(response.text)
            return ""

        response = response.json()
        print(response)
        experience_merged: str = response["experience_merged"]
        print(f"experience_merged={experience_merged}")
        return experience_merged
    
    def update_experience(self, trajectories):
        response = requests.post(url=self.experience_base_url + "summarizer", json={
            "workspace_id": self.experience_workspace_id,
            "traj_list": trajectories,
        })
        response.raise_for_status()
        response = response.json()
        print(f"add new experiences: {response["experience_list"]}")
    
    def call_llm(self, messages: list, tool_schemas: list[dict]) -> str:
        for i in range(100):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                # Change this function to modify the base llm
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=tool_schemas,
                    temperature=self.temperature,
                    seed=0,
                    extra_body={"enable_thinking": self.enable_thinking},
                    stream=self.enable_thinking,
                    parallel_tool_calls=True,
                )
                if not self.enable_thinking:
                    out_msg = response.choices[0].message
                    return out_msg.model_dump(exclude_unset=True, exclude_none=True)
                else:
                    reasoning_content = ""  # Complete reasoning process
                    answer_content = ""     # Define complete response
                    tool_info = []          # Store tool invocation information
                    is_answering = False   # Determine whether the reasoning process has finished and response has started
                    
                    for chunk in response:
                        if not chunk.choices:
                            # Handle usage information
                            continue
                        else:
                            delta = chunk.choices[0].delta
                            # Handle AI's thought process (chain reasoning)
                            if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                                reasoning_content += delta.reasoning_content
                                
                            # Handle final response content
                            else:
                                if not is_answering:  # Print title when entering the response phase for the first time
                                    is_answering = True
                                if delta.content is not None:
                                    answer_content += delta.content
                                
                                # Handle tool invocation information (support parallel tool calls)
                                if delta.tool_calls is not None:
                                    for tool_call in delta.tool_calls:
                                        index = tool_call.index  # Tool call index, used for parallel calls
                                        
                                        # Dynamically expand tool information storage list
                                        while len(tool_info) <= index:
                                            tool_info.append({"id": "", "type": "function", "index": index, "function": { "name": "", "arguments": "" }})
                                        
                                        # Collect tool call ID (used for subsequent function calls)
                                        if tool_call.id:
                                            tool_info[index]['id'] += tool_call.id
                                    
                                        # Collect function name (used for subsequent routing to specific functions)
                                        if tool_call.function and tool_call.function.name:
                                            tool_info[index]['function']['name'] += tool_call.function.name
                                        
                                        # Collect function parameters (in JSON string format, need subsequent parsing)
                                        if tool_call.function and tool_call.function.arguments:
                                            tool_info[index]['function']['arguments'] += tool_call.function.arguments
                    msg = {
                        "role": "assistant",
                        "content": answer_content,
                        "reasoning_content": reasoning_content,
                    }
                    if tool_info:
                        msg["tool_calls"] = tool_info
                    return msg
            except Exception as e:
                logger.exception(f"encounter error with {e.args}")
                time.sleep(1 + i * 10)

        return "call llm error"

    def env_step(self, run_id: int, index: int, messages: str) -> str:
        """
        Process one step in the conversation.
        Both single turn and multi turn are supported.

        Args:
            messages: List of conversation messages, with the last one being assistant response
            test_entry: Test entry containing initial_config, involved_classes, question etc.
            **kwargs: Additional arguments for compatibility

        Returns:
            Dict containing next message and tools if applicable
        """
        try:
            if not messages: 
                return handle_user_turn(self.original_test_entry[run_id][index], self.current_turn[run_id][index])

            if messages[-1]["role"] != "assistant":
                return create_error_response(
                    "Last message must be from assistant"
                )

            if "tool_calls" in messages[-1] and len(messages[-1]["tool_calls"]) > 0:
                try:
                    tool_calls = messages[-1]["tool_calls"]
                    decoded_calls = self._convert_tool_calls_to_execution_format(
                        tool_calls
                    )
                    # decoded_calls:[function(param=xxx)]
                    print(f"decoded_calls: {decoded_calls}")
                    # todo 实现decode_execute，返回prm
                    # if self.decode_execute(decoded_calls):
                    if is_empty_execute_response(decoded_calls):
                        warnings.warn(
                            f"is_empty_execute_response: {is_empty_execute_response(decoded_calls)}"
                        )
                        return handle_user_turn(self.original_test_entry[run_id][index], self.current_turn[run_id][index])
                    return handle_tool_calls(
                        tool_calls, decoded_calls, self.original_test_entry[run_id][index], self.current_turn[run_id][index]
                    )
                except Exception as e:
                    warnings.warn(f"处理工具调用时发生错误: {str(e)}")
                    return handle_user_turn(self.original_test_entry[run_id][index], self.current_turn[run_id][index])
            else:
                return handle_user_turn(self.original_test_entry[run_id][index], self.current_turn[run_id][index])

        except Exception as e:
            return create_error_response(f"处理请求时发生错误: {str(e)}")

    def _convert_tool_calls_to_execution_format(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Convert OpenAI format tool calls to execution format.

        Args:
            tool_calls: List of tool calls in OpenAI format

        Returns:
            List of function calls in string format
        """
        execution_list = []

        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            function_name = function.get("name", "")

            try:
                arguments = function.get("arguments", "{}")
                if isinstance(arguments, str):
                    args_dict = json.loads(arguments)
                else:
                    args_dict = arguments

                args_str = ", ".join([f"{k}={repr(v)}" for k, v in args_dict.items()])
                execution_list.append(f"{function_name}({args_str})")

            except Exception as e:
                execution_list.append(f"{function_name}()")

        return execution_list
    
    def get_reward(self, run_id, index) -> float:
        try:
            if not self.history[run_id][index] or not self.original_test_entry[run_id][index]:
                return 0.0

            model_name = "env_handler"
            handler = QwenAPIHandler(
                model_name, temperature=1.0
            )  # FIXME: magic number

            model_result_data = self._convert_conversation_to_eval_format(run_id, index)

            prompt_data = [self.original_test_entry[run_id][index]]

            state = {"leaderboard_table": {}}
            record_cost_latency(
                state["leaderboard_table"], model_name, [model_result_data]
            )

            if is_relevance_or_irrelevance(self.categories[index]):
                accuracy, _ = self._eval_relevance_test(
                    handler, model_result_data, prompt_data, model_name, self.category
                )
            else:
                # Find the corresponding possible answer file

                possible_answer_file = find_file_with_suffix(
                    self.answer_path, self.categories[index]
                )
                possible_answer = load_file(possible_answer_file, sort_by_id=True)
                possible_answer = [
                    item for item in possible_answer if item["id"] == self.task_ids[index]
                ]
                if is_multi_turn(self.categories[index]):
                    accuracy, _ = self._eval_multi_turn_test(
                        handler,
                        model_result_data,
                        prompt_data,
                        possible_answer,
                        model_name,
                        self.categories[index],
                    )
                else:
                    accuracy, _ = self._eval_single_turn_test(
                        handler,
                        model_result_data,
                        prompt_data,
                        possible_answer,
                        model_name,
                        self.categories[index],
                    )
            print(f"model_result_data: {model_result_data}")
            print(f"possible_answer: {possible_answer}") if possible_answer else None

            return accuracy

        except Exception as e:
            import traceback

            traceback.print_exc()
            return 0
    
    def _convert_conversation_to_eval_format(self, run_id, index) -> Dict[str, Any]:
        """
        Convert conversation history to evaluation format.

        Args:
            conversation_result: Result from run_conversation
            original_test_entry: Original test entry data

        Returns:
            Data in format expected by multi_turn_runner or other runners
        """
        if is_multi_turn(self.categories[index]):
            turns_data = extract_multi_turn_responses(self.history[run_id][index])
        else:
            turns_data = extract_single_turn_response(self.history[run_id][index])

        model_result_data = {
            "id": self.task_ids[index],
            "result": turns_data,
            "latency": 0,
            "input_token_count": 0,
            "output_token_count": 0,
        }

        return model_result_data
    
    def _eval_multi_turn_test(
        self,
        handler,
        model_result_data,
        prompt_data,
        possible_answer,
        model_name,
        test_category,
    ):
        """
        Evaluate multi-turn test.

        Args:
            handler: Model handler instance
            model_result_data: Model result data
            prompt_data: Prompt data
            possible_answer: Possible answer data
            model_name: Name of the model
            test_category: Category of the test

        Returns:
            Tuple of (accuracy, total_count)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            score_dir = Path(temp_dir)
            accuracy, total_count = multi_turn_runner(
                handler=handler,
                model_result=[model_result_data],
                prompt=prompt_data,
                possible_answer=possible_answer,
                model_name=model_name,
                test_category=test_category,
                score_dir=score_dir,
            )
            capture_and_print_score_files(
                score_dir, model_name, test_category, "multi_turn"
            )
            return accuracy, total_count
    
    def _eval_single_turn_test(
        self,
        handler,
        model_result_data,
        prompt_data,
        possible_answer,
        model_name,
        test_category,
    ):
        """
        Evaluate single-turn AST test.

        Args:
            handler: Model handler instance
            model_result_data: Model result data
            prompt_data: Prompt data
            possible_answer: Possible answer data
            model_name: Name of the model
            test_category: Category of the test

        Returns:
            Tuple of (accuracy, total_count)
        """
        language = "Python"
        if "java" in test_category.lower():
            language = "Java"
        elif "js" in test_category.lower() or "javascript" in test_category.lower():
            language = "JavaScript"

        with tempfile.TemporaryDirectory() as temp_dir:
            score_dir = Path(temp_dir)
            accuracy, total_count = ast_file_runner(
                handler=handler,
                model_result=[model_result_data],
                prompt=prompt_data,
                possible_answer=possible_answer,
                language=language,
                test_category=test_category,
                model_name=model_name,
                score_dir=score_dir,
            )
            capture_and_print_score_files(
                score_dir, model_name, test_category, "single_turn"
            )
            return accuracy, total_count

    def execute(self):
        result = []
        for task_index, task_id in enumerate(tqdm(self.task_ids, desc=f"ray_index={self.index}")):
            for run_id in range(self.num_runs):
                try:
                    for i in range(self.max_interactions):
                        llm_output = self.call_llm(self.history[run_id][task_index], self.tool_schema[run_id][task_index])
                        self.history[run_id][task_index].append(llm_output)

                        env_output = self.env_step(run_id, task_index, self.history[run_id][task_index])
                        # 与环境交互后env_output有以下几种返回情况: 
                        # 1. 触发query, 附带着available tools列表, {"messages": [{"role": "user", "content": user_query}], "tools": tools} 
                        # 2. 返回工具调用结果, {"messages": [{"role": "tool", "content": {<execution_results>}, 'tool_call_id': 'chatcmpl-tool-xxx'}]}
                        #    <execution_results>: 正确执行时返回结果dict, e.g., {"travel_cost_list": [1140.0]}, 错误时返回error信息, e.g., {"error": "cd: temporary: No such directory. You cannot use path to change directory."}
                        # 3. 回合结束, 返回{"messages": [{"role": "env", "content": "[CONVERSATION_COMPLETED]"}]}
                        # 4. 程序出错, 返回{"messages": [{"role": "env", "content": f"[ERROR] {error_message}"}]}
            
                        # tool_list更新
                        if "tools" in env_output:
                            self.tool_schema[run_id][task_index] = extract_tool_schema(env_output["tools"])
                        
                        new_tool_calls=[]
                        new_tool_call_ids=[]
                        next_user_msg = ""
                        for idx, msg in enumerate(env_output.get("messages", [])):
                            if msg["role"] == "tool" and len(msg["content"])>0: 
                                new_tool_calls.append(msg.get("content", ""))
                                new_tool_call_ids.append(msg.get("tool_call_id", ""))
                            elif msg["role"] == "user":
                                next_user_msg = msg.get("content", "")
                                self.current_turn[run_id][task_index] += 1
                            else: # for env role messages
                                next_user_msg = msg.get("content", "")
                                
                        if new_tool_calls:
                            for idx, call in enumerate(new_tool_calls):
                                self.history[run_id][task_index].append({"role": "tool", "content": str(call), "tool_call_id": new_tool_call_ids[idx]})
                        else:
                            self.history[run_id][task_index].append({"role": "user", "content": next_user_msg})

                        logger.info(f"index={self.index} task_id={task_id} iteration={i}")

                        if self.task_completed(run_id, task_index):
                            break

                    reward = self.get_reward(run_id, task_index)
                    if reward == 1 and not self.use_fixed_experience:
                        self.update_experience([{
                            "task_id":task_id,
                            "messages":self.history[run_id][task_index],
                            "score":reward
                        }]) # selectively add experiences when succeed
                     
                    t_result = {
                        "run_id": run_id,
                        "task_id": self.task_ids[task_index],
                        "experiment_name": self.experiment_name,
                        "task_completed": self.task_completed(run_id, task_index),
                        "reward": reward,
                        "task_history": self.history[run_id][task_index],
                    }
                    result.append(t_result)

                except Exception as e:
                    logger.exception(f"encounter error with {e.args}")
                    result.append({})
        return result

    def task_completed(self, run_id, index):
        """
        Check if task is completed.

        Returns:
            True if task is completed, False otherwise
        """
        return self.history[run_id][index][-1]["content"] == "[CONVERSATION_COMPLETED]"

def main():
    with open(os.getenv("BFCL_DATA_PATH"), "r", encoding="utf-8") as f:
        task_ids = [json.loads(l)["id"] for l in f]
    dataset_name = "dev"
    agent = BFCLAgent(
        index=0, 
        task_id=task_ids[0], 
        experiment_name=f"zouying_{dataset_name}", 
    )
    result = agent.execute()
    logger.info(f"result={json.dumps(result)}")


if __name__ == "__main__":
    main()
