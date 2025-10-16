import asyncio
from typing import List

from flowllm import C, BaseAsyncOp
from flowllm.enumeration.role import Role
from flowllm.schema.message import Message
from flowllm.schema.vector_node import VectorNode
from flowllm.utils.common_utils import extract_content
from loguru import logger

from reme_ai.schema.memory import ToolMemory, vector_node_to_memory


@C.register_op()
class SummaryToolMemoryOp(BaseAsyncOp):
    file_path: str = __file__

    def __init__(self,
                 recent_call_count: int = 30,
                 summary_sleep_interval: float = 1.0,
                 **kwargs):
        super().__init__(**kwargs)
        self.recent_call_count: int = recent_call_count
        self.summary_sleep_interval: float = summary_sleep_interval

    @staticmethod
    def _format_call_summaries_markdown(recent_calls: List) -> str:
        """Format tool call summaries as markdown."""
        if not recent_calls:
            return "No recent calls available."

        lines = []
        for i, call in enumerate(recent_calls, 1):
            lines.append(f"### Call #{i}")
            lines.append(f"- **Summary**: {call.summary}")
            lines.append(f"- **Evaluation**: {call.evaluation}")
            lines.append(f"- **Score**: {call.score}")
            lines.append(f"- **Success**: {call.success}")
            lines.append(f"- **Time Cost**: {call.time_cost}s")
            lines.append(f"- **Token Cost**: {call.token_cost}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_statistics_markdown(statistics: dict) -> str:
        """Format statistics as markdown."""
        lines = [f"- **Total Calls**: {statistics.get('total_calls', 0)}",
                 f"- **Recent Calls**: {statistics.get('recent_calls', 0)}",
                 f"- **Success Rate**: {statistics.get('success_rate', 0):.2%}",
                 f"- **Recent Success Rate**: {statistics.get('recent_success_rate', 0):.2%}",
                 f"- **Average Score**: {statistics.get('avg_score', 0):.3f}",
                 f"- **Recent Average Score**: {statistics.get('recent_avg_score', 0):.3f}",
                 f"- **Average Time Cost**: {statistics.get('avg_time_cost', 0):.3f}s",
                 f"- **Average Token Cost**: {statistics.get('avg_token_cost', 0):.1f}"]

        return "\n".join(lines)

    async def _summarize_single_tool(self, tool_memory: ToolMemory, index: int) -> ToolMemory:
        await asyncio.sleep(self.summary_sleep_interval * index)

        # Get the most recent N tool calls
        recent_calls = tool_memory.tool_call_results[-self.recent_call_count:]

        if not recent_calls:
            logger.warning(f"No tool call results found for tool: {tool_memory.when_to_use}")
            return tool_memory

        # Get statistics
        statistics = tool_memory.statistic(recent_frequency=self.recent_call_count)

        # Format data as markdown
        call_summaries_md = self._format_call_summaries_markdown(recent_calls)
        statistics_md = self._format_statistics_markdown(statistics)

        prompt = self.prompt_format(prompt_name="summarize_tool_usage_prompt",
                                    tool_name=tool_memory.when_to_use,
                                    call_summaries=call_summaries_md,
                                    statistics=statistics_md)

        def parse_summary(message: Message) -> ToolMemory:
            content = message.content.strip()
            # Extract content from txt code block
            tool_memory.content = extract_content(content, "txt")

            # Update modified time
            tool_memory.update_modified_time()

            logger.info(f"Summarized tool {index}: tool_name={tool_memory.when_to_use}, "
                        f"content_length={len(tool_memory.content)}")
            return tool_memory

        # Call LLM to generate summary
        result = await self.llm.achat(messages=[Message(role=Role.USER, content=prompt)], callback_fn=parse_summary)

        return result

    async def async_execute(self):
        tool_names: str = self.context.get("tool_names", "")
        workspace_id: str = self.context.workspace_id

        if not tool_names:
            logger.warning("tool_names is empty, skipping processing")
            self.context.response.answer = "tool_names is required"
            self.context.response.success = False
            return

        # Split tool names by comma
        tool_name_list = [name.strip() for name in tool_names.split(",") if name.strip()]
        logger.info(f"workspace_id={workspace_id} processing {len(tool_name_list)} tools: {tool_name_list}")

        # Search for each tool in the vector store
        matched_tool_memories: List[ToolMemory] = []

        for tool_name in tool_name_list:
            nodes: List[VectorNode] = await self.vector_store.async_search(query=tool_name,
                                                                           workspace_id=workspace_id,
                                                                           top_k=1)

            if nodes:
                top_node = nodes[0]
                memory = vector_node_to_memory(top_node)

                # Ensure it's a ToolMemory and when_to_use matches
                if isinstance(memory, ToolMemory) and memory.when_to_use == tool_name:
                    matched_tool_memories.append(memory)
                    logger.info(f"Found tool_memory for tool_name={tool_name}, "
                                f"memory_id={memory.memory_id}, "
                                f"total_calls={len(memory.tool_call_results)}")
                else:
                    logger.warning(f"No exact match found for tool_name={tool_name}")
            else:
                logger.warning(f"No memory found for tool_name={tool_name}")

        if not matched_tool_memories:
            logger.info("No matching tool memories found")
            self.context.response.answer = "No matching tool memories found"
            self.context.response.success = False
            return

        # Concurrently summarize all tool memories
        logger.info(f"Starting concurrent summarization of {len(matched_tool_memories)} tool memories")

        # 使用基类的 submit_async_task 提交所有总结任务
        for index, tool_memory in enumerate(matched_tool_memories):
            self.submit_async_task(self._summarize_single_tool, tool_memory, index)

        # 使用基类的 join_async_task 等待所有任务完成
        # 注意: 基类已经过滤掉异常,返回的只包含成功的结果
        valid_summarized_memories = await self.join_async_task(return_exceptions=True)
        logger.info(f"Completed summarization of {len(valid_summarized_memories)} tool memories")

        # Set response
        self.context.response.answer = f"Successfully summarized {len(valid_summarized_memories)} tool memories"
        self.context.response.success = True
        self.context.response.metadata["memory_list"] = valid_summarized_memories
        self.context.response.metadata["deleted_memory_ids"] = [m.memory_id for m in valid_summarized_memories]

        # Log summary for each tool
        for memory in valid_summarized_memories:
            logger.info(f"Tool: {memory.when_to_use}, "
                        f"Content: {memory.content[:100]}...")


async def main():
    from flowllm.app import FlowLLMApp
    from reme_ai.summary.tool.parse_tool_call_result_op import ParseToolCallResultOp
    from reme_ai.vector_store.update_vector_store_op import UpdateVectorStoreOp
    from datetime import datetime, timedelta
    import random

    async with FlowLLMApp(load_default_config=True):
        workspace_id = "test_workspace_complex"
        tool_name = "web_search_tool"

        # ===== 第一步: 准备 30 条模拟的工具调用记录 =====
        # 模拟不同场景的调用记录:成功、参数错误、超时、返回空结果等
        logger.info("=" * 80)
        logger.info("步骤1: 准备 30 条工具调用记录,模拟真实使用场景")
        logger.info("=" * 80)

        base_time = datetime.now() - timedelta(days=7)
        tool_call_results = []

        # 场景1: 成功的搜索 (15条)
        success_queries = [
            "Python asyncio tutorial", "machine learning basics", "React hooks guide",
            "Docker best practices", "SQL optimization tips", "Git workflow strategies",
            "RESTful API design", "microservices architecture", "Redis caching patterns",
            "Kubernetes deployment", "GraphQL advantages", "MongoDB schema design",
            "JWT authentication", "OAuth2 flow", "WebSocket real-time"
        ]

        for i, query in enumerate(success_queries):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=i * 2)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": query,
                    "max_results": random.randint(5, 20),
                    "language": "en",
                    "filter_type": "technical_docs"
                },
                "output": f"Found {random.randint(8, 20)} relevant results for '{query}'. Top results include official documentation, tutorials, and best practice guides.",
                "token_cost": random.randint(100, 300),
                "success": True,
                "time_cost": round(random.uniform(1.5, 3.5), 2)
            })

        # 场景2: 参数不合理导致的部分成功 (8条)
        for i in range(8):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=30 + i * 3)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": f"test query {i}",  # 查询词过于简单
                    "max_results": 100,  # 请求过多结果
                    "language": "unknown",  # 语言参数错误
                },
                "output": f"Warning: language 'unknown' not supported, using default. Query too generic, returning limited results. Found {random.randint(2, 5)} results.",
                "token_cost": random.randint(50, 150),
                "success": True,
                "time_cost": round(random.uniform(2.0, 4.0), 2)
            })

        # 场景3: 超时或失败 (5条)
        for i in range(5):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=54 + i * 4)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": f"extremely complex query with many conditions {i}",
                    "max_results": 50,
                    "language": "en",
                    "filter_type": "all"
                },
                "output": "Error: Request timeout after 10 seconds. Try simplifying the query or reducing max_results.",
                "token_cost": 20,
                "success": False,
                "time_cost": 10.0
            })

        # 场景4: 空结果 (2条)
        for i in range(2):
            tool_call_results.append({
                "create_time": (base_time + timedelta(hours=74 + i * 5)).strftime("%Y-%m-%d %H:%M:%S"),
                "tool_name": tool_name,
                "input": {
                    "query": f"xyzabc123nonexistent{i}",  # 不存在的内容
                    "max_results": 10,
                    "language": "en",
                },
                "output": "No results found for the given query. Please try different keywords.",
                "token_cost": 30,
                "success": True,
                "time_cost": 1.2
            })

        logger.info(f"准备了 {len(tool_call_results)} 条工具调用记录")
        logger.info(f"- 成功调用: 15 条")
        logger.info(f"- 参数不合理: 8 条")
        logger.info(f"- 超时失败: 5 条")
        logger.info(f"- 空结果: 2 条")

        # ===== 第二步: 使用 ParseToolCallResultOp >> UpdateVectorStoreOp 串联运行 =====
        logger.info("\n" + "=" * 80)
        logger.info("步骤2: ParseToolCallResultOp >> UpdateVectorStoreOp 串联评估并保存")
        logger.info("=" * 80)

        # 使用 >> 操作符串联两个Op,自动传递context和metadata
        pipeline = ParseToolCallResultOp(evaluation_sleep_interval=0.1) >> UpdateVectorStoreOp()
        
        await pipeline.async_call(
            tool_call_results=tool_call_results,
            tool_name=tool_name,
            workspace_id=workspace_id
        )

        if not pipeline.context.response.success:
            logger.error(f"Pipeline failed: {pipeline.context.response.answer}")
            return

        logger.info(f"✓ Pipeline 完成")
        logger.info(f"  评估了 {len(tool_call_results)} 条记录")
        logger.info(f"  每条记录包含: summary, evaluation, score (0.0/0.5/1.0)")

        # 显示一些评估结果示例
        memory_list = pipeline.context.response.metadata.get("memory_list", [])
        if memory_list:
            tool_memory = memory_list[0]
            logger.info(f"\n评估结果示例 (前3条):")
            for i, result in enumerate(tool_memory.tool_call_results[:3], 1):
                logger.info(f"  调用 #{i}:")
                logger.info(f"    查询: {result.input.get('query', 'N/A')}")
                logger.info(f"    评分: {result.score}")
                logger.info(f"    总结: {result.summary[:80]}...")
                logger.info(f"    评价: {result.evaluation[:80]}...")

        # 显示向量数据库更新结果
        update_result = pipeline.context.response.metadata.get("update_result", {})
        logger.info(f"\n✓ 向量数据库更新完成:")
        logger.info(f"  删除记录数: {update_result.get('deleted_count', 0)}")
        logger.info(f"  插入记录数: {update_result.get('inserted_count', 0)}")

        # ===== 第三步: 使用 SummaryToolMemoryOp 总结工具使用模式 =====
        logger.info("\n" + "=" * 80)
        logger.info("步骤3: 使用 SummaryToolMemoryOp 从 30 条记录中提取使用模式和建议")
        logger.info("=" * 80)

        summary_op = SummaryToolMemoryOp(
            recent_call_count=30,  # 分析最近30条记录
            summary_sleep_interval=0.5
        )
        await summary_op.async_call(
            tool_names=tool_name,
            workspace_id=workspace_id
        )

        if not summary_op.context.response.success:
            logger.error(f"SummaryToolMemoryOp failed: {summary_op.context.response.answer}")
            return

        logger.info(f"✓ SummaryToolMemoryOp 完成")

        # ===== 第四步: 展示 summary 的价值 =====
        logger.info("\n" + "=" * 80)
        logger.info("步骤4: 展示 Summary 如何将分散的调用记录转化为有价值的使用指南")
        logger.info("=" * 80)

        summarized_memories = summary_op.context.response.metadata.get("memory_list", [])
        if summarized_memories:
            summarized_memory = summarized_memories[0]

            logger.info(f"\n工具名称: {summarized_memory.when_to_use}")
            logger.info(f"\n统计信息:")
            stats = summarized_memory.statistic(recent_frequency=30)
            logger.info(f"  总调用次数: {stats['total_calls']}")
            logger.info(f"  成功率: {stats['success_rate']:.1%}")
            logger.info(f"  平均评分: {stats['avg_score']:.2f}")
            logger.info(f"  平均耗时: {stats['avg_time_cost']:.2f}s")
            logger.info(f"  平均Token消耗: {stats['avg_token_cost']:.1f}")

            logger.info(f"\n" + "=" * 60)
            logger.info("Summary 生成的使用指南 (从30条分散记录中提取):")
            logger.info("=" * 60)
            logger.info(summarized_memory.content)
            logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
