# Tool Memory 效果验证基准测试

## 概述

本文档设计了一个完整的实验方案来验证 Tool Memory 在提升 Agent 性能方面的有效性。实验通过对比 Agent 在有无 Tool Memory 支持下的表现，量化评估 Tool Memory 的实际效果。

## 实验设计

### 1. 环境构建

#### 1.1 三个 Mock 搜索工具

设计三个具有不同性能特征的模拟搜索工具：

- **SearchToolA**: 快速但浅层搜索
- **SearchToolB**: 平衡性能和质量
- **SearchToolC**: 全面但成本高

每个工具的接口定义：
```python
def search_tool(query: str, scenario: str) -> dict:
    """
    Args:
        query: 搜索查询字符串
        scenario: 场景标识符
    
    Returns:
        {
            "result": str,           # 搜索结果
            "token_cost": int,       # 消耗的 token 数
            "time_cost": float,      # 耗时(秒)
            "quality_score": float,  # 质量评分 0-1
            "success": bool          # 是否成功
        }
    """
```

#### 1.2 三个场景设计

**场景 1: 简单事实查询 (Simple Factual Queries)**
- 特征: 查询简短，答案直接明确
- 最佳工具: SearchToolA (快速，质量足够)
- 示例查询:
  - "法国的首都是什么？"
  - "Python 是什么时候首次发布的？"
  - "地球上有几个大洲？"
  - "水的沸点是多少度？"
  - "谁发明了电话？"

**场景 2: 复杂研究查询 (Complex Research Queries)**
- 特征: 多维度问题，需要全面深入的搜索
- 最佳工具: SearchToolC (高质量，值得成本)
- 示例查询:
  - "比较凯恩斯主义和奥地利学派的经济政策"
  - "分析可再生能源采用对环境的影响"
  - "解释量子力学和广义相对论之间的关系"
  - "讨论人工智能的历史演变过程"
  - "评估不同机器学习算法在 NLP 中的有效性"

**场景 3: 中等复杂度查询 (Moderate Complexity Queries)**
- 特征: 中等难度，需要平衡的性能
- 最佳工具: SearchToolB (最优的成本-质量权衡)
- 示例查询:
  - "列举 Python 3.10 的主要特性"
  - "微服务架构有哪些好处？"
  - "解释区块链技术的工作原理"
  - "描述 SQL 和 NoSQL 数据库的主要区别"
  - "软件工程中常见的设计模式有哪些？"

#### 1.3 工具性能矩阵

| 工具 / 场景 | 场景 1 (简单) | 场景 2 (复杂) | 场景 3 (中等) |
|------------|--------------|--------------|--------------|
| **SearchToolA** | ⭐⭐⭐ 最佳 | ❌ 差 | ⚠️ 可接受 |
| **SearchToolB** | ⭐⭐ 良好 | ⭐⭐ 良好 | ⭐⭐⭐ 最佳 |
| **SearchToolC** | ⭐ 过度 | ⭐⭐⭐ 最佳 | ⭐⭐ 良好 |

**详细性能指标：**

```
场景 1 (简单):
- SearchToolA: token_cost=100-200,  time_cost=0.5-1s,   quality=0.85-0.95, success_rate=0.95
- SearchToolB: token_cost=300-500,  time_cost=1-2s,     quality=0.90-0.98, success_rate=0.98
- SearchToolC: token_cost=800-1200, time_cost=3-5s,     quality=0.90-0.95, success_rate=0.90

场景 2 (复杂):
- SearchToolA: token_cost=150-250,  time_cost=0.5-1s,   quality=0.40-0.60, success_rate=0.50
- SearchToolB: token_cost=400-600,  time_cost=1.5-2.5s, quality=0.70-0.85, success_rate=0.85
- SearchToolC: token_cost=1000-1500, time_cost=3-6s,    quality=0.90-0.98, success_rate=0.95

场景 3 (中等):
- SearchToolA: token_cost=120-220,  time_cost=0.5-1s,   quality=0.65-0.75, success_rate=0.75
- SearchToolB: token_cost=350-550,  time_cost=1-2s,     quality=0.85-0.95, success_rate=0.95
- SearchToolC: token_cost=900-1300, time_cost=3-5s,     quality=0.85-0.92, success_rate=0.92
```

### 2. 基准实验（无 Tool Memory）

#### 2.1 实验设置

1. **Agent 配置**:
   - LLM: GPT-4 或同等模型
   - 可用工具: SearchToolA, SearchToolB, SearchToolC
   - 无历史性能数据

2. **测试数据集**:
   - 每个场景 5 个查询 × 3 个场景 = 共 15 个查询
   - 随机顺序执行，避免学习偏差

3. **预期行为**:
   - Agent 仅基于工具描述做决策
   - 无历史性能数据可参考
   - 可能出现次优工具选择

#### 2.2 执行流程

```python
# 伪代码
for query in test_queries:
    scenario = identify_scenario(query)
    
    # Agent 在没有 memory 指导的情况下选择工具
    selected_tool = agent.select_tool(
        query=query,
        available_tools=[SearchToolA, SearchToolB, SearchToolC]
    )
    
    # 执行工具
    result = selected_tool.execute(query, scenario)
    
    # 记录执行详情
    log_execution({
        "query": query,
        "scenario": scenario,
        "tool": selected_tool.name,
        "token_cost": result.token_cost,
        "time_cost": result.time_cost,
        "quality_score": result.quality_score,
        "success": result.success,
        "timestamp": current_time()
    })
```

#### 2.3 数据采集

将执行日志保存到: `baseline_execution_log.jsonl`

格式（对应 `ToolCallResult` schema）:
```json
{
  "create_time": "2025-10-16 10:30:00",
  "tool_name": "SearchToolA",
  "input": {
    "query": "法国的首都是什么？",
    "scenario": "simple"
  },
  "output": "法国的首都是巴黎。巴黎是法国最大的城市...",
  "token_cost": 150,
  "success": true,
  "time_cost": 0.8,
  "summary": "成功返回法国首都的准确信息",
  "evaluation": "回答准确简洁，符合简单查询的需求",
  "score": 0.92,
  "metadata": {
    "experiment_id": "baseline_001",
    "query_id": "q001",
    "scenario": "simple"
  }
}
```

#### 2.4 追踪指标

**按场景指标:**
- 总 token 成本
- 总时间成本
- 平均质量评分
- 成功率
- 工具选择分布

**总体指标:**
- 汇总 token 成本
- 汇总时间成本
- 总体平均质量
- 总体成功率
- 工具选择效率（最优选择百分比）

### 3. 生成 Tool Memory

#### 3.1 Tool Memory Service 集成

使用基准实验的执行日志生成 Tool Memory：

```python
from reme_ai.service.task_memory_service import TaskMemoryService
from reme_ai.summary.tool import SummaryToolMemoryOp
from reme_ai.schema.memory import ToolMemory, ToolCallResult
import json

# 初始化服务
# 注意：当前版本使用 TaskMemoryService 来管理 ToolMemory
# ToolMemory 是通过 memory_type="tool" 来区分的
tool_memory_service = TaskMemoryService(
    vector_store_config={
        "vector_store_type": "chroma",
        "persist_directory": "./memory_vector_store"
    }
)

# 处理基准执行日志
tool_memories = {}  # {tool_name: ToolMemory}

with open("baseline_execution_log.jsonl", "r") as f:
    for line in f:
        record = json.loads(line)
        tool_name = record["tool_name"]
        
        # 为每个工具创建或更新 ToolMemory
        if tool_name not in tool_memories:
            tool_memories[tool_name] = ToolMemory(
                workspace_id="tool_bench_experiment",
                memory_type="tool",
                when_to_use=f"{tool_name} 的使用场景和性能统计",
                content="",  # 将在汇总时填充
                tool_call_results=[]
            )
        
        # 添加 ToolCallResult
        tool_call_result = ToolCallResult(**record)
        tool_memories[tool_name].tool_call_results.append(tool_call_result)

# 使用 SummaryToolMemoryOp 生成 memory 内容
summary_op = SummaryToolMemoryOp()
for tool_name, tool_memory in tool_memories.items():
    # 汇总工具性能
    summary_result = summary_op.summarize_tool_performance(
        tool_memory=tool_memory
    )
    
    # 更新 content 和 when_to_use
    tool_memory.content = summary_result["content"]
    tool_memory.when_to_use = summary_result["when_to_use"]
    
    # 存储到向量数据库
    tool_memory_service.add_memory(tool_memory)
```

#### 3.2 预期 Tool Memory 内容

基于 `ToolMemory` schema，每个工具的 memory 应包含：

**ToolMemory 结构:**
```python
{
    "workspace_id": "tool_bench_experiment",
    "memory_id": "auto_generated_uuid",
    "memory_type": "tool",
    "when_to_use": "工具使用场景的简洁描述，用于检索匹配",
    "content": "详细的工具性能分析和使用建议",
    "score": 0.85,  # 综合评分
    "time_created": "2025-10-16 10:30:00",
    "time_modified": "2025-10-16 10:30:00",
    "author": "tool_bench_system",
    "tool_call_results": [
        # 所有的 ToolCallResult 记录
    ],
    "metadata": {
        "tool_name": "SearchToolA",
        "total_calls": 15,
        "scenarios_tested": ["simple", "complex", "moderate"]
    }
}
```

**示例: SearchToolA 的 Tool Memory**

```python
ToolMemory(
    workspace_id="tool_bench_experiment",
    memory_type="tool",
    when_to_use="快速简单查询，事实性问题，需要低延迟响应的场景",
    content="""
## SearchToolA 性能分析

### 最佳使用场景
- **简单事实查询 (场景1)**: 
  - 平均 token 成本: 150
  - 平均耗时: 0.8秒
  - 平均质量: 0.90
  - 成功率: 95%
  - **推荐指数: ⭐⭐⭐⭐⭐**

### 不适用场景
- **复杂研究查询 (场景2)**:
  - 平均质量仅 0.50，成功率 50%
  - 无法提供深度分析
  - **强烈不推荐**

- **中等复杂度查询 (场景3)**:
  - 质量 0.70，可接受但不是最优
  - 建议考虑 SearchToolB

### 统计数据 (最近20次调用)
- 总调用次数: 15
- 平均 token 成本: 150
- 平均耗时: 0.8秒
- 平均质量评分: 0.72
- 成功率: 73%

### 使用建议
1. 优先用于简单、直接的事实查询
2. 需要快速响应时的首选
3. 避免用于需要深度分析的复杂问题
4. 成本最低，适合高频调用场景
""",
    score=0.72,
    tool_call_results=[...],  # 所有调用记录
    metadata={
        "tool_name": "SearchToolA",
        "best_scenario": "simple",
        "worst_scenario": "complex"
    }
)
```

#### 3.3 使用 statistic() 方法

利用 `ToolMemory.statistic()` 方法获取统计信息：

```python
# 获取最近20次调用的统计
stats = tool_memory.statistic(recent_frequency=20)

# 返回格式:
{
    "total_calls": 15,
    "recent_calls_analyzed": 15,
    "avg_token_cost": 150.5,
    "success_rate": 0.7333,
    "avg_time_cost": 0.850,
    "avg_score": 0.720
}
```

### 4. 增强实验（有 Tool Memory）

#### 4.1 实验设置

1. **Agent 配置**:
   - 同基准实验的 LLM
   - 可用工具: SearchToolA, SearchToolB, SearchToolC
   - **新增**: 可访问每个工具的 Tool Memory

2. **测试数据集**:
   - 与基准实验相同的 15 个查询
   - 相同的执行顺序以确保公平对比

3. **预期行为**:
   - Agent 在选择工具前检索 Tool Memory
   - 基于历史性能数据做出明智决策
   - 每个场景选择最优工具

#### 4.2 执行流程

```python
from reme_ai.retrieve.tool import RetrieveToolMemoryOp

# 初始化检索操作
retrieve_op = RetrieveToolMemoryOp()

for query in test_queries:
    scenario = identify_scenario(query)
    
    # 检索每个工具的 Tool Memory
    tool_memories = {}
    for tool in [SearchToolA, SearchToolB, SearchToolC]:
        # 使用 RetrieveToolMemoryOp 检索相关 memory
        memories = retrieve_op.retrieve(
            workspace_id="tool_bench_experiment",
            query=query,
            tool_name=tool.name,
            top_k=1
        )
        
        if memories:
            tool_memory = memories[0]
            # 获取统计信息
            stats = tool_memory.statistic(recent_frequency=20)
            tool_memories[tool.name] = {
                "when_to_use": tool_memory.when_to_use,
                "content": tool_memory.content,
                "statistics": stats
            }
    
    # Agent 基于 memory 选择工具
    selected_tool = agent.select_tool_with_memory(
        query=query,
        available_tools=[SearchToolA, SearchToolB, SearchToolC],
        tool_memories=tool_memories
    )
    
    # 执行工具
    result = selected_tool.execute(query, scenario)
    
    # 记录执行详情（同基准实验格式）
    tool_call_result = ToolCallResult(
        create_time=current_time(),
        tool_name=selected_tool.name,
        input={"query": query, "scenario": scenario},
        output=result.output,
        token_cost=result.token_cost,
        success=result.success,
        time_cost=result.time_cost,
        summary=result.summary,
        evaluation=result.evaluation,
        score=result.score,
        metadata={
            "experiment_id": "enhanced_001",
            "memory_used": True,
            "scenario": scenario
        }
    )
    
    log_execution(tool_call_result.model_dump())
```

#### 4.3 数据采集

保存执行日志到: `enhanced_execution_log.jsonl`

格式与基准实验相同，但在 metadata 中增加 `memory_used: true` 标记。

### 5. 对比分析

#### 5.1 指标对比

创建两个实验的对比表：

| 指标 | 基准实验 (无 Memory) | 增强实验 (有 Memory) | 改进幅度 |
|------|---------------------|---------------------|----------|
| **总 Token 成本** | X tokens | Y tokens | -Z% |
| **总时间成本** | X 秒 | Y 秒 | -Z% |
| **平均质量评分** | X.XX | Y.YY | +Z% |
| **总体成功率** | X% | Y% | +Z% |
| **最优工具选择率** | X% | Y% | +Z% |

#### 5.2 按场景分析

使用 Python 脚本分析每个场景的性能：

```python
import json
from collections import defaultdict
from reme_ai.schema.memory import ToolCallResult

def analyze_by_scenario(log_file):
    """分析执行日志，按场景统计"""
    scenario_stats = defaultdict(lambda: {
        "calls": [],
        "tool_distribution": defaultdict(int)
    })
    
    with open(log_file, "r") as f:
        for line in f:
            record = json.loads(line)
            scenario = record["metadata"]["scenario"]
            
            # 添加调用记录
            scenario_stats[scenario]["calls"].append(
                ToolCallResult(**record)
            )
            
            # 统计工具分布
            scenario_stats[scenario]["tool_distribution"][
                record["tool_name"]
            ] += 1
    
    # 计算每个场景的指标
    results = {}
    for scenario, data in scenario_stats.items():
        calls = data["calls"]
        results[scenario] = {
            "total_calls": len(calls),
            "avg_token_cost": sum(c.token_cost for c in calls) / len(calls),
            "avg_time_cost": sum(c.time_cost for c in calls) / len(calls),
            "avg_quality": sum(c.score for c in calls) / len(calls),
            "success_rate": sum(1 for c in calls if c.success) / len(calls),
            "tool_distribution": dict(data["tool_distribution"])
        }
    
    return results

# 分析两个实验
baseline_results = analyze_by_scenario("baseline_execution_log.jsonl")
enhanced_results = analyze_by_scenario("enhanced_execution_log.jsonl")

# 打印对比
for scenario in ["simple", "complex", "moderate"]:
    print(f"\n场景: {scenario}")
    print(f"Token 成本: {baseline_results[scenario]['avg_token_cost']:.1f} -> "
          f"{enhanced_results[scenario]['avg_token_cost']:.1f}")
    print(f"时间成本: {baseline_results[scenario]['avg_time_cost']:.2f}s -> "
          f"{enhanced_results[scenario]['avg_time_cost']:.2f}s")
    print(f"质量评分: {baseline_results[scenario]['avg_quality']:.2f} -> "
          f"{enhanced_results[scenario]['avg_quality']:.2f}")
```

#### 5.3 预期结果

**场景 1 (简单查询):**
- 基准: 可能混用三个工具，平均成本较高
- 增强: 主要使用 SearchToolA，成本降低，质量保持

**场景 2 (复杂查询):**
- 基准: 可能误用 SearchToolA，质量和成功率低
- 增强: 主要使用 SearchToolC，质量和成功率显著提升

**场景 3 (中等查询):**
- 基准: 工具选择随机，性能不稳定
- 增强: 主要使用 SearchToolB，最优的成本-质量平衡

#### 5.4 统计显著性检验

```python
from scipy import stats
import numpy as np

def significance_test(baseline_log, enhanced_log, metric="token_cost"):
    """对指定指标进行 t 检验"""
    baseline_values = []
    enhanced_values = []
    
    with open(baseline_log) as f:
        for line in f:
            record = json.loads(line)
            baseline_values.append(record[metric])
    
    with open(enhanced_log) as f:
        for line in f:
            record = json.loads(line)
            enhanced_values.append(record[metric])
    
    # 执行 t 检验
    t_stat, p_value = stats.ttest_ind(baseline_values, enhanced_values)
    
    return {
        "metric": metric,
        "baseline_mean": np.mean(baseline_values),
        "enhanced_mean": np.mean(enhanced_values),
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant": p_value < 0.05
    }

# 测试各项指标
for metric in ["token_cost", "time_cost", "score"]:
    result = significance_test(
        "baseline_execution_log.jsonl",
        "enhanced_execution_log.jsonl",
        metric
    )
    print(f"\n{metric} 检验结果:")
    print(f"  基准均值: {result['baseline_mean']:.2f}")
    print(f"  增强均值: {result['enhanced_mean']:.2f}")
    print(f"  p-value: {result['p_value']:.4f}")
    print(f"  显著性: {'是' if result['significant'] else '否'}")
```

#### 5.5 可视化

生成对比图表：

```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # 支持中文

def plot_comparison():
    """生成对比可视化图表"""
    
    # 1. 工具选择分布对比
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    scenarios = ["simple", "complex", "moderate"]
    
    for idx, scenario in enumerate(scenarios):
        baseline = baseline_results[scenario]["tool_distribution"]
        enhanced = enhanced_results[scenario]["tool_distribution"]
        
        x = np.arange(3)
        width = 0.35
        
        axes[idx].bar(x - width/2, 
                     [baseline.get(f"SearchTool{t}", 0) for t in ["A", "B", "C"]],
                     width, label='基准')
        axes[idx].bar(x + width/2,
                     [enhanced.get(f"SearchTool{t}", 0) for t in ["A", "B", "C"]],
                     width, label='增强')
        
        axes[idx].set_title(f'场景: {scenario}')
        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(['ToolA', 'ToolB', 'ToolC'])
        axes[idx].legend()
    
    plt.tight_layout()
    plt.savefig('tool_selection_comparison.png')
    
    # 2. 性能指标对比
    metrics = ['Token成本', '时间成本', '质量评分', '成功率']
    # ... 更多可视化代码
```

### 6. 实现指南

#### 6.1 目录结构

```
cookbook/tool_memory/
├── __init__.py
├── mock_tools.py              # Mock 搜索工具实现
├── scenarios.py               # 场景定义和查询
├── baseline_experiment.py     # 运行基准实验
├── generate_memory.py         # 生成 Tool Memory
├── enhanced_experiment.py     # 运行增强实验
├── analysis.py                # 对比分析
├── visualization.py           # 生成图表
├── requirements.txt           # 依赖项
├── README.md                  # 实验说明
└── data/
    ├── baseline_execution_log.jsonl
    ├── enhanced_execution_log.jsonl
    ├── tool_memories/         # 生成的 Tool Memory
    └── analysis_results.json
```

#### 6.2 运行基准测试

```bash
# 步骤 1: 运行基准实验（无 Tool Memory）
python cookbook/tool_memory/baseline_experiment.py \
    --output data/baseline_execution_log.jsonl \
    --workspace-id tool_bench_experiment

# 步骤 2: 生成 Tool Memory
python cookbook/tool_memory/generate_memory.py \
    --input data/baseline_execution_log.jsonl \
    --workspace-id tool_bench_experiment \
    --vector-store-path ./memory_vector_store

# 步骤 3: 运行增强实验（有 Tool Memory）
python cookbook/tool_memory/enhanced_experiment.py \
    --output data/enhanced_execution_log.jsonl \
    --workspace-id tool_bench_experiment \
    --vector-store-path ./memory_vector_store

# 步骤 4: 分析结果
python cookbook/tool_memory/analysis.py \
    --baseline data/baseline_execution_log.jsonl \
    --enhanced data/enhanced_execution_log.jsonl \
    --output data/analysis_results.json

# 步骤 5: 生成可视化
python cookbook/tool_memory/visualization.py \
    --analysis data/analysis_results.json \
    --output-dir data/figures/
```

#### 6.3 核心代码示例

**mock_tools.py:**
```python
import random
import time
from reme_ai.schema.memory import ToolCallResult

class MockSearchTool:
    """Mock 搜索工具基类"""
    
    def __init__(self, name: str, performance_matrix: dict):
        self.name = name
        self.performance_matrix = performance_matrix
    
    def execute(self, query: str, scenario: str) -> ToolCallResult:
        """执行搜索并返回结果"""
        perf = self.performance_matrix[scenario]
        
        # 模拟执行时间
        time_cost = random.uniform(perf["time_range"][0], perf["time_range"][1])
        time.sleep(time_cost)
        
        # 生成结果
        token_cost = random.randint(perf["token_range"][0], perf["token_range"][1])
        quality = random.uniform(perf["quality_range"][0], perf["quality_range"][1])
        success = random.random() < perf["success_rate"]
        
        result = ToolCallResult(
            create_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            tool_name=self.name,
            input={"query": query, "scenario": scenario},
            output=self._generate_output(query, success),
            token_cost=token_cost,
            success=success,
            time_cost=time_cost,
            summary=f"{'成功' if success else '失败'}执行查询: {query[:30]}...",
            evaluation=self._generate_evaluation(quality, scenario),
            score=quality if success else quality * 0.5,
            metadata={"scenario": scenario}
        )
        
        return result
    
    def _generate_output(self, query: str, success: bool) -> str:
        """生成模拟输出"""
        if success:
            return f"针对查询 '{query}' 的搜索结果...\n[模拟的详细内容]"
        else:
            return f"无法完成查询: {query}"
    
    def _generate_evaluation(self, quality: float, scenario: str) -> str:
        """生成评估说明"""
        if quality > 0.85:
            return f"高质量回答，非常适合{scenario}场景"
        elif quality > 0.70:
            return f"良好回答，适合{scenario}场景"
        else:
            return f"回答质量不足，不适合{scenario}场景"

# 创建三个工具实例
SearchToolA = MockSearchTool("SearchToolA", {
    "simple": {
        "token_range": (100, 200),
        "time_range": (0.5, 1.0),
        "quality_range": (0.85, 0.95),
        "success_rate": 0.95
    },
    "complex": {
        "token_range": (150, 250),
        "time_range": (0.5, 1.0),
        "quality_range": (0.40, 0.60),
        "success_rate": 0.50
    },
    "moderate": {
        "token_range": (120, 220),
        "time_range": (0.5, 1.0),
        "quality_range": (0.65, 0.75),
        "success_rate": 0.75
    }
})

SearchToolB = MockSearchTool("SearchToolB", {
    "simple": {
        "token_range": (300, 500),
        "time_range": (1.0, 2.0),
        "quality_range": (0.90, 0.98),
        "success_rate": 0.98
    },
    "complex": {
        "token_range": (400, 600),
        "time_range": (1.5, 2.5),
        "quality_range": (0.70, 0.85),
        "success_rate": 0.85
    },
    "moderate": {
        "token_range": (350, 550),
        "time_range": (1.0, 2.0),
        "quality_range": (0.85, 0.95),
        "success_rate": 0.95
    }
})

SearchToolC = MockSearchTool("SearchToolC", {
    "simple": {
        "token_range": (800, 1200),
        "time_range": (3.0, 5.0),
        "quality_range": (0.90, 0.95),
        "success_rate": 0.90
    },
    "complex": {
        "token_range": (1000, 1500),
        "time_range": (3.0, 6.0),
        "quality_range": (0.90, 0.98),
        "success_rate": 0.95
    },
    "moderate": {
        "token_range": (900, 1300),
        "time_range": (3.0, 5.0),
        "quality_range": (0.85, 0.92),
        "success_rate": 0.92
    }
})

TOOL_REGISTRY = {
    "SearchToolA": SearchToolA,
    "SearchToolB": SearchToolB,
    "SearchToolC": SearchToolC
}
```

**scenarios.py:**
```python
"""场景和查询定义"""

TEST_QUERIES = [
    # 场景 1: 简单事实查询
    {"query": "法国的首都是什么？", "scenario": "simple"},
    {"query": "Python 是什么时候首次发布的？", "scenario": "simple"},
    {"query": "地球上有几个大洲？", "scenario": "simple"},
    {"query": "水的沸点是多少度？", "scenario": "simple"},
    {"query": "谁发明了电话？", "scenario": "simple"},
    
    # 场景 2: 复杂研究查询
    {"query": "比较凯恩斯主义和奥地利学派的经济政策", "scenario": "complex"},
    {"query": "分析可再生能源采用对环境的影响", "scenario": "complex"},
    {"query": "解释量子力学和广义相对论之间的关系", "scenario": "complex"},
    {"query": "讨论人工智能的历史演变过程", "scenario": "complex"},
    {"query": "评估不同机器学习算法在 NLP 中的有效性", "scenario": "complex"},
    
    # 场景 3: 中等复杂度查询
    {"query": "列举 Python 3.10 的主要特性", "scenario": "moderate"},
    {"query": "微服务架构有哪些好处？", "scenario": "moderate"},
    {"query": "解释区块链技术的工作原理", "scenario": "moderate"},
    {"query": "描述 SQL 和 NoSQL 数据库的主要区别", "scenario": "moderate"},
    {"query": "软件工程中常见的设计模式有哪些？", "scenario": "moderate"}
]

OPTIMAL_TOOL_MAPPING = {
    "simple": "SearchToolA",
    "complex": "SearchToolC",
    "moderate": "SearchToolB"
}
```

#### 6.4 预期成果

**假设验证**: Tool Memory 应该带来：

1. ✅ **降低 Token 成本**: 通过选择更高效的工具，降低 20-30%
2. ✅ **降低时间成本**: 通过最优工具选择，降低 15-25%
3. ✅ **提升质量评分**: 平均质量提升 10-15%
4. ✅ **提高成功率**: 总体成功率提升 5-10%
5. ✅ **优化工具选择**: 最优工具选择率从 33%（随机）提升到 60-80%

**具体示例预期:**

```
基准实验 (15次调用):
- 总 Token 成本: 7,500
- 总时间: 30秒
- 平均质量: 0.75
- 成功率: 78%
- 最优选择率: 40% (6/15)

增强实验 (15次调用):
- 总 Token 成本: 5,250 (↓30%)
- 总时间: 22秒 (↓27%)
- 平均质量: 0.88 (↑17%)
- 成功率: 91% (↑13%)
- 最优选择率: 87% (13/15) (↑117%)
```

### 7. 进阶实验

#### 7.1 在线学习实验

测试 Tool Memory 的在线更新和学习能力：

```python
def online_learning_experiment():
    """在线学习实验：从零开始逐步构建 Tool Memory"""
    
    # 初始化空 Tool Memory
    tool_memories = {
        "SearchToolA": ToolMemory(workspace_id="online_learning"),
        "SearchToolB": ToolMemory(workspace_id="online_learning"),
        "SearchToolC": ToolMemory(workspace_id="online_learning")
    }
    
    learning_curve = []
    
    for idx, test_case in enumerate(TEST_QUERIES):
        # 基于当前 memory 选择工具
        selected_tool = agent.select_tool_with_memory(
            query=test_case["query"],
            tool_memories=tool_memories
        )
        
        # 执行并记录
        result = selected_tool.execute(
            test_case["query"], 
            test_case["scenario"]
        )
        
        # 立即更新对应工具的 Tool Memory
        tool_memories[selected_tool.name].tool_call_results.append(result)
        
        # 重新汇总 memory
        update_tool_memory_content(tool_memories[selected_tool.name])
        
        # 记录学习曲线
        is_optimal = (selected_tool.name == 
                     OPTIMAL_TOOL_MAPPING[test_case["scenario"]])
        learning_curve.append({
            "call_index": idx + 1,
            "is_optimal": is_optimal,
            "cumulative_optimal_rate": sum(lc["is_optimal"] 
                                          for lc in learning_curve) / (idx + 1)
        })
    
    return learning_curve
```

#### 7.2 Memory 时效性实验

测试 Tool Memory 对工具性能变化的适应性：

```python
def memory_decay_experiment():
    """测试当工具性能发生变化时，memory 的适应能力"""
    
    # 阶段 1: 使用原始性能矩阵，构建 Tool Memory
    phase1_results = run_baseline_experiment()
    tool_memories = generate_tool_memories(phase1_results)
    
    # 阶段 2: 改变工具性能（例如 ToolA 性能下降）
    SearchToolA.performance_matrix["simple"]["quality_range"] = (0.50, 0.60)
    SearchToolA.performance_matrix["simple"]["success_rate"] = 0.60
    
    # 阶段 3: 使用旧 memory 运行新实验
    phase2_results = run_enhanced_experiment(
        tool_memories=tool_memories,
        update_memory=False  # 不更新 memory
    )
    
    # 阶段 4: 允许 memory 更新，观察适应过程
    phase3_results = run_enhanced_experiment(
        tool_memories=tool_memories,
        update_memory=True,  # 在线更新 memory
        update_frequency=5   # 每5次调用更新一次
    )
    
    return {
        "phase1": phase1_results,  # 原始性能，有 memory
        "phase2": phase2_results,  # 性能变化，旧 memory
        "phase3": phase3_results   # 性能变化，memory 适应
    }
```

#### 7.3 跨域迁移实验

测试 Tool Memory 在不同但相关场景间的迁移能力：

```python
def cross_domain_experiment():
    """测试 Tool Memory 的跨域迁移能力"""
    
    # 定义新的场景：技术文档查询
    NEW_SCENARIOS = {
        "api_reference": {
            "queries": ["Python requests 库的 GET 方法参数", ...],
            "optimal_tool": "SearchToolB"
        },
        "troubleshooting": {
            "queries": ["如何修复 CORS 错误", ...],
            "optimal_tool": "SearchToolC"
        },
        "quick_lookup": {
            "queries": ["HTTP 状态码 404 的含义", ...],
            "optimal_tool": "SearchToolA"
        }
    }
    
    # 使用原场景训练的 Tool Memory
    tool_memories = load_tool_memories("tool_bench_experiment")
    
    # 在新场景测试
    transfer_results = run_experiment_with_new_scenarios(
        scenarios=NEW_SCENARIOS,
        tool_memories=tool_memories
    )
    
    # 对比：1) 无 memory, 2) 有旧 memory, 3) 新场景训练的 memory
    return compare_transfer_effectiveness(transfer_results)
```

### 8. 数据分析和可视化

#### 8.1 生成分析报告

```python
def generate_report():
    """生成完整的实验分析报告"""
    
    report = {
        "experiment_metadata": {
            "date": datetime.now().isoformat(),
            "total_queries": 15,
            "scenarios": 3,
            "tools": 3
        },
        "baseline_summary": analyze_experiment("baseline_execution_log.jsonl"),
        "enhanced_summary": analyze_experiment("enhanced_execution_log.jsonl"),
        "comparison": {
            "token_cost_reduction": calculate_reduction("token_cost"),
            "time_cost_reduction": calculate_reduction("time_cost"),
            "quality_improvement": calculate_improvement("score"),
            "success_rate_improvement": calculate_improvement("success"),
            "optimal_selection_improvement": calculate_optimal_selection_rate()
        },
        "statistical_tests": {
            "token_cost_ttest": significance_test("token_cost"),
            "time_cost_ttest": significance_test("time_cost"),
            "quality_ttest": significance_test("score")
        },
        "by_scenario_analysis": {
            "simple": analyze_scenario("simple"),
            "complex": analyze_scenario("complex"),
            "moderate": analyze_scenario("moderate")
        },
        "tool_memory_effectiveness": {
            "SearchToolA": evaluate_memory_impact("SearchToolA"),
            "SearchToolB": evaluate_memory_impact("SearchToolB"),
            "SearchToolC": evaluate_memory_impact("SearchToolC")
        }
    }
    
    # 保存为 JSON
    with open("data/analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 生成 Markdown 报告
    generate_markdown_report(report)
    
    return report
```

#### 8.2 关键可视化图表

1. **工具选择分布热力图**
2. **成本-质量散点图**
3. **学习曲线图（在线学习实验）**
4. **Memory 影响力雷达图**
5. **时间线对比图**

### 9. 结论

本基准测试框架提供了全面的 Tool Memory 效果验证方案，确保：

- **公平对比**: 相同查询、相同工具、受控环境
- **清晰指标**: token 成本、时间、质量、成功率的量化改进
- **可重复性**: 详细步骤和数据收集规范
- **统计严谨性**: 显著性检验和置信区间
- **符合 Schema**: 完全基于 `reme_ai/schema/memory.py` 中的数据结构

**预期结论**: Tool Memory 应该展现出明显的优势，帮助 Agent 做出明智的工具选择决策，在效率和效果上都有可测量的提升。

---

## 参考资料

- Tool Memory Schema: `/reme_ai/schema/memory.py`
- Tool Memory 文档: `/docs/tool_memory/tool_memory.md`
- Tool Memory 实现: `/reme_ai/summary/tool/`
- Tool 检索操作: `/docs/tool_memory/tool_retrieve_ops.md`
- Tool 汇总操作: `/docs/tool_memory/tool_summary_ops.md`
