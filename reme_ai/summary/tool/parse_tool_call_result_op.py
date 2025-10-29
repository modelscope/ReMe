import asyncio
from collections import defaultdict
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

    @staticmethod
    def _is_valid_tool_call_result(tool_call_result: ToolCallResult) -> bool:
        """
        Validate if a tool call result is valid and should be processed.
        
        Args:
            tool_call_result: The tool call result to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check if tool_name is provided
        if not tool_call_result.tool_name or not tool_call_result.tool_name.strip():
            logger.warning("Skipping tool_call_result: tool_name is empty")
            return False

        # Check if output is provided (empty output means no useful result)
        if not tool_call_result.output or not str(tool_call_result.output).strip():
            logger.warning(f"Skipping tool_call_result for {tool_call_result.tool_name}: output is empty")
            return False

        # Check if input is provided
        if tool_call_result.input is None or (
                isinstance(tool_call_result.input, str) and not tool_call_result.input.strip()
        ) or (
                isinstance(tool_call_result.input, dict) and not tool_call_result.input
        ):
            logger.warning(f"Skipping tool_call_result for {tool_call_result.tool_name}: input is empty")
            return False

        return True

    @staticmethod
    def _estimate_token_cost(tool_call_result: ToolCallResult) -> int:
        """
        Estimate token cost based on input and output length.
        Uses the approximation: token_count ≈ char_count / 4
        
        Args:
            tool_call_result: The tool call result to estimate tokens for
            
        Returns:
            Estimated token count as an integer
        """
        # Convert input to string
        if isinstance(tool_call_result.input, dict):
            input_str = str(tool_call_result.input)
        else:
            input_str = str(tool_call_result.input)

        # Get output string
        output_str = str(tool_call_result.output)

        # Calculate total character count
        total_chars = len(input_str) + len(output_str)

        # Estimate tokens (1 token ≈ 4 characters for English text)
        estimated_tokens = total_chars // 4

        return estimated_tokens

    @staticmethod
    def _format_tool_memories_summary(memory_list: List[ToolMemory], deleted_memory_ids: List[str]) -> str:
        """Format tool memories update summary"""
        lines = []
        
        # 统计信息
        total_tools = len(memory_list)
        updated_tools = len(deleted_memory_ids)
        new_tools = total_tools - updated_tools
        
        lines.append(f"Processed {total_tools} tool(s): {updated_tools} updated, {new_tools} newly created\n")
        
        # 详细信息
        for idx, memory in enumerate(memory_list, 1):
            is_updated = memory.memory_id in deleted_memory_ids
            status = "Updated" if is_updated else "New"
            
            lines.append(f"[{status}] {memory.when_to_use}")
            lines.append(f"  Total calls: {len(memory.tool_call_results)}")
            
            # 显示最近添加的调用结果统计
            if memory.tool_call_results:
                recent_results = memory.tool_call_results[-3:]
                success_count = sum(1 for r in recent_results if r.success)
                avg_score = sum(r.score for r in recent_results) / len(recent_results)
                lines.append(f"  Recent calls: {success_count}/{len(recent_results)} successful, avg score: {avg_score:.2f}")
            
            if idx < len(memory_list):
                lines.append("")
        
        return "\n".join(lines)

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

            # 验证 score 是否符合 2 档要求 (0.0, 1.0)
            if tool_call_result.score not in [0.0, 1.0]:
                if tool_call_result.score < 0.5:
                    tool_call_result.score = 0.0
                else:
                    tool_call_result.score = 1.0

            # 打印完整的prompt和result
            logger.info(f"\n{'='*80}\nLLM Evaluation [Index {index}]\n{'='*80}\n"
                       f"PROMPT:\n{prompt}\n\n"
                       f"RESULT:\n{content}\n"
                       f"{'='*80}\n")
            
            return tool_call_result

        # 调用 LLM 进行评估
        result = await self.llm.achat(messages=[Message(role=Role.USER, content=prompt)], callback_fn=parse_evaluation)

        return result

    async def async_execute(self):
        tool_call_results: list = self.context.get("tool_call_results", [])
        tool_call_results = [ToolCallResult(**x) if isinstance(x, dict) else x for x in tool_call_results]
        workspace_id: str = self.context.workspace_id

        if not tool_call_results:
            self.context.response.answer = "No valid tool_call_results"
            self.context.response.success = False
            return

        # 过滤和验证 tool_call_results
        original_count = len(tool_call_results)
        valid_tool_call_results = []
        
        for tool_call_result in tool_call_results:
            # 验证数据是否有效
            if not self._is_valid_tool_call_result(tool_call_result):
                continue

            # 确保有 hash 值
            tool_call_result.ensure_hash()

            # 如果 token_cost 未设置（默认值 -1），则自动计算
            if tool_call_result.token_cost < 0:
                token_cost = self._estimate_token_cost(tool_call_result)
                tool_call_result.token_cost = token_cost
                logger.info(f"Auto-calculated token_cost={token_cost} for tool={tool_call_result.tool_name}")

            valid_tool_call_results.append(tool_call_result)

        # 记录过滤统计
        filtered_count = original_count - len(valid_tool_call_results)
        if filtered_count > 0:
            logger.warning(f"Filtered out {filtered_count} invalid tool_call_results out of {original_count}")

        # 如果所有记录都被过滤了
        if not valid_tool_call_results:
            self.context.response.answer = f"All {original_count} tool_call_results were invalid and filtered out"
            self.context.response.success = False
            return

        logger.info(f"Processing {len(valid_tool_call_results)} valid tool_call_results")

        # 使用基类的 submit_async_task 提交所有评估任务
        for index, tool_call_result in enumerate(valid_tool_call_results):
            self.submit_async_task(self._evaluate_single_tool_call, tool_call_result, index)

        # 使用基类的 join_async_task 等待所有任务完成
        # 注意: 基类已经过滤掉异常,返回的只包含成功的结果
        evaluated_results = await self.join_async_task(return_exceptions=True)

        tool_results_by_name = defaultdict(list)
        for result in evaluated_results:
            tool_results_by_name[result.tool_name].append(result)

        # 处理每个 tool_name 的结果
        all_memory_list = []
        all_deleted_memory_ids = []
        deduplication_stats = {"total_new": 0, "deduplicated": 0, "added": 0}

        for tool_name, tool_call_results in tool_results_by_name.items():
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

            # 如果没有找到匹配的 memory，创建新的
            if tool_memory is None:
                tool_memory = ToolMemory(workspace_id=workspace_id, when_to_use=tool_name)

            # 获取现有的所有 hash 值用于去重
            existing_hashes = {result.call_hash for result in tool_memory.tool_call_results if result.call_hash}
            
            # 过滤掉重复的 tool_call_results
            new_results = []
            for result in tool_call_results:
                deduplication_stats["total_new"] += 1
                if result.call_hash not in existing_hashes:
                    new_results.append(result)
                    existing_hashes.add(result.call_hash)
                    deduplication_stats["added"] += 1
                else:
                    deduplication_stats["deduplicated"] += 1
                    logger.info(f"Skipping duplicate tool call for {tool_name} with hash {result.call_hash}")
            
            # 只添加非重复的结果
            tool_memory.tool_call_results.extend(new_results)

            # 保留最近的 n 个
            if len(tool_memory.tool_call_results) > self.max_history_tool_call_cnt:
                tool_memory.tool_call_results = tool_memory.tool_call_results[-self.max_history_tool_call_cnt:]

            # 更新修改时间
            tool_memory.update_modified_time()

            # 如果是更新现有的 memory，需要先删除旧的
            if exist_node:
                all_deleted_memory_ids.append(tool_memory.memory_id)

            all_memory_list.append(tool_memory)

        # 格式化结果信息
        formatted_answer = self._format_tool_memories_summary(all_memory_list, all_deleted_memory_ids)

        # 添加过滤统计信息
        if filtered_count > 0:
            filter_info = (f"\n\nValidation Summary:\n"
                           f"  Total input: {original_count}\n"
                           f"  Valid: {len(valid_tool_call_results)}\n"
                           f"  Filtered (invalid): {filtered_count}")
            formatted_answer += filter_info
        
        # 添加去重统计信息
        dedup_info = (f"\n\nDeduplication Summary:\n"
                     f"  Total new calls: {deduplication_stats['total_new']}\n"
                     f"  Added: {deduplication_stats['added']}\n"
                     f"  Deduplicated: {deduplication_stats['deduplicated']}")
        formatted_answer += dedup_info
        
        # 设置返回结果
        self.context.response.answer = formatted_answer
        self.context.response.success = True
        self.context.response.metadata["deleted_memory_ids"] = all_deleted_memory_ids
        self.context.response.metadata["memory_list"] = all_memory_list
        self.context.response.metadata["validation_stats"] = {
            "total_input": original_count,
            "valid": len(valid_tool_call_results),
            "filtered": filtered_count
        }
        self.context.response.metadata["deduplication_stats"] = deduplication_stats


async def main():
    """Simple test for ParseToolCallResultOp"""
    from datetime import datetime

    from reme_ai.app import ReMeApp

    async with ReMeApp():
        op = ParseToolCallResultOp()

        # Create test data with different scenarios
        tool_call_results = [
            # Test 1: Valid with explicit token_cost
            {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "test_tool_with_token",
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
            },
            # Test 2: Valid without token_cost (should auto-calculate)
            {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "test_tool_auto_token",
                "input": {
                    "query": "get weather information for San Francisco",
                    "units": "celsius"
                },
                "output": "Current weather in San Francisco: Temperature: 18°C, Humidity: 65%, Conditions: Partly cloudy",
                # token_cost not provided, will be auto-calculated
                "success": True,
                "time_cost": 1.5
            },
            # Test 3: Invalid - empty output (should be filtered)
            {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "invalid_tool_empty_output",
                "input": {"query": "test"},
                "output": "",  # Empty output
                "success": False,
                "time_cost": 0.1
            },
            # Test 4: Invalid - empty input (should be filtered)
            {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "invalid_tool_empty_input",
                "input": {},  # Empty dict input
                "output": "Some output",
                "success": True,
                "time_cost": 0.2
            },
            # Test 5: Invalid - missing tool_name (should be filtered)
            {
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": "",  # Empty tool name
                "input": {"test": "data"},
                "output": "Result",
                "success": True,
                "time_cost": 0.3
            }
        ]

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing with {len(tool_call_results)} tool_call_results")
        logger.info(f"Expected: 2 valid, 3 filtered")
        logger.info(f"{'=' * 60}\n")
        workspace_id = "test_workspace1"

        await op.async_call(tool_call_results=tool_call_results, workspace_id=workspace_id)
        logger.info(f"Response: {op.context.response.model_dump_json()}")


if __name__ == "__main__":
    asyncio.run(main())
