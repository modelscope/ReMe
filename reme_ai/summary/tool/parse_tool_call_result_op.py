import asyncio
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from flowllm.schema.vector_node import VectorNode
from flowllm.utils.common_utils import extract_content
from loguru import logger

from reme_ai.schema.memory import ToolMemory, ToolCallResult, vector_node_to_memory


@C.register_op()
class ParseToolCallResultOp(BaseAsyncOp):
    file_path: str = __file__

    def __init__(self,
                 max_history_tool_call_cnt: int = 100,
                 evaluation_sleep_interval: float = 1.0,
                 **kwargs):
        super().__init__(**kwargs)
        self.max_history_tool_call_cnt: int = max_history_tool_call_cnt
        self.evaluation_sleep_interval: float = evaluation_sleep_interval

    async def _evaluate_single_tool_call(self, tool_call_result: ToolCallResult, index: int) -> ToolCallResult:
        await asyncio.sleep(self.evaluation_sleep_interval * index)

        prompt = self.prompt_format(
            prompt_name="evaluate_tool_call_prompt",
            tool_name=tool_call_result.tool_name,
            input_params=str(tool_call_result.input),
            output=tool_call_result.output,
            success_flag=str(tool_call_result.success),
            time_cost=tool_call_result.time_cost,
            token_cost=tool_call_result.token_cost)

        def parse_evaluation(message: Message) -> ToolCallResult:
            content = message.content.strip()
            eval_data = extract_content(content, "json")

            # 更新 tool_call_result - 包含 summary, evaluation 和 score
            tool_call_result.summary = eval_data.get("summary", "")
            tool_call_result.evaluation = eval_data.get("evaluation", "")
            tool_call_result.score = float(eval_data.get("score", 0.0))

            # 验证 score 是否符合 3 档要求 (0.0, 0.5, 1.0)
            if tool_call_result.score not in [0.0, 0.5, 1.0]:
                logger.warning(f"Score {tool_call_result.score} not in [0.0, 0.5, 1.0], rounding to nearest")
                if tool_call_result.score < 0.25:
                    tool_call_result.score = 0.0
                elif tool_call_result.score < 0.75:
                    tool_call_result.score = 0.5
                else:
                    tool_call_result.score = 1.0

            logger.info(f"Evaluated tool call {index}: tool_name={tool_call_result.tool_name}, "
                        f"score={tool_call_result.score}, summary={tool_call_result.summary[:50]}...")
            return tool_call_result

        # 调用 LLM 进行评估
        result = await self.llm.achat(messages=[Message(role=Role.USER, content=prompt)], callback_fn=parse_evaluation)

        return result

    async def async_execute(self):
        tool_call_results: list = self.context.get("tool_call_results", [])
        tool_call_results = [ToolCallResult(**x) if isinstance(x, dict) else x for x in tool_call_results]
        tool_name: str = self.context.get("tool_name", "")
        workspace_id: str = self.context.workspace_id
        logger.info(f"workspace_id={workspace_id} count={len(tool_call_results)} tool_name={tool_name}")

        if not tool_name:
            logger.warning("tool_name is empty, skipping processing")
            self.context.response.answer = "tool_name is required"
            self.context.response.success = False
            return

        if not tool_call_results:
            logger.info("No valid tool_call_results to process")
            self.context.response.answer = "No valid tool_call_results"
            self.context.response.success = False
            return

        # 并发评估所有 tool_call_results
        logger.info(f"Starting concurrent evaluation of {len(tool_call_results)} tool call results")
        
        # 使用基类的 submit_async_task 提交所有评估任务
        for index, tool_call_result in enumerate(tool_call_results):
            self.submit_async_task(self._evaluate_single_tool_call, tool_call_result, index)

        # 使用基类的 join_async_task 等待所有任务完成
        # 注意: 基类已经过滤掉异常,返回的只包含成功的结果
        tool_call_results = await self.join_async_task(return_exceptions=True)
        logger.info(f"Completed evaluation of {len(tool_call_results)} tool call results")

        nodes: List[VectorNode] = await self.vector_store.async_search(query=tool_name,
                                                                       workspace_id=workspace_id,
                                                                       top_k=1)

        tool_memory: ToolMemory | None = None
        exist_node: bool = False

        if nodes:
            top_node = nodes[0]
            memory: ToolMemory = vector_node_to_memory(top_node)

            # 确保是 ToolMemory 类型且 when_to_use 与 tool_name 匹配
            if isinstance(memory, ToolMemory) and memory.when_to_use == tool_name:
                tool_memory = memory
                exist_node = True
                logger.info(f"Found existing tool_memory for tool_name={tool_name}, memory_id={tool_memory.memory_id}")
            else:
                logger.info(f"Top result does not match tool_name={tool_name}, will create new memory")

        # 如果没有找到匹配的 memory，创建新的
        if tool_memory is None:
            tool_memory = ToolMemory(workspace_id=workspace_id, when_to_use=tool_name)
            logger.info(f"Created new tool_memory for tool_name={tool_name}, memory_id={tool_memory.memory_id}")

        tool_memory.tool_call_results.extend(tool_call_results)

        # 保留最近的 n 个
        if len(tool_memory.tool_call_results) > self.max_history_tool_call_cnt:
            tool_memory.tool_call_results = tool_memory.tool_call_results[-self.max_history_tool_call_cnt:]
            logger.info(f"Trimmed tool_call_results to {self.max_history_tool_call_cnt} most recent entries")

        # 更新修改时间
        tool_memory.update_modified_time()

        # 4. 将更新后的 memory 保存到向量数据库
        # 如果是更新现有的 memory，需要先删除旧的
        deleted_memory_ids = []
        if exist_node:
            deleted_memory_ids = [tool_memory.memory_id]

        # 设置返回结果
        self.context.response.metadata["deleted_memory_ids"] = deleted_memory_ids
        self.context.response.metadata["memory_list"] = [tool_memory]

        logger.info(f"Updated tool_memory: tool_name={tool_name}, total_results={len(tool_memory.tool_call_results)}")


async def main():
    """Simple test for ParseToolCallResultOp"""
    from flowllm.app import FlowLLMApp
    from datetime import datetime
    
    async with FlowLLMApp(load_default_config=True):
        op = ParseToolCallResultOp()

        # Create simple test data
        tool_call_results = [
            {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "test_tool",
                "input": {
                    "query": "search for python asyncio documentation",
                    "max_results": 10,
                    "filter_type": "official_docs",
                    "language": "en"
                },
                "output": "Found 10 relevant documentation pages for Python asyncio. Top results include: 1) Official Python docs for asyncio module, 2) Real Python asyncio tutorial, 3) Stack Overflow asyncio examples. All results are from official sources as requested.",
                "token_cost": 150,
                "success": True,
                "time_cost": 2.3
            }
        ]
        tool_name = "test_tool"
        workspace_id = "test_workspace1"

        await op.async_call(tool_call_results=tool_call_results, tool_name=tool_name, workspace_id=workspace_id)
        logger.info(f"Response: {op.context.response.model_dump_json()}")


if __name__ == "__main__":
    asyncio.run(main())
