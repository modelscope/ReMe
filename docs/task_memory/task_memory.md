# Task Memory in ReMe

Task Memory is a key component of ReMe that allows AI agents to learn from memories and improve their performance on similar tasks in the future. This document explains how task memory works and how to use it in your applications.

## What is Task Memory?

Task Memory represents knowledge extracted from previous task executions, including:
- Successful approaches to solving problems
- Common pitfalls and failures to avoid
- Comparative insights between different approaches

Each task memory contains:
- `when_to_use`: Conditions that indicate when this memory is relevant
- `content`: The actual knowledge or experience to be applied
- `score`: Quality score of the memory (assigned during validation)
- Metadata about the memory's source and utility

## Task Memory的数据结构

### TaskMemory

```python
class TaskMemory(BaseMemory):
    memory_type: str = "task"
    workspace_id: str       # 工作空间ID
    memory_id: str          # 记忆的唯一ID
    when_to_use: str        # 何时使用此记忆的条件
    content: str            # 具体的经验内容
    score: float            # 质量评分（validation阶段设置）
    time_created: str       # 创建时间
    time_modified: str      # 最后修改时间
    author: str             # 创建者（通常是LLM模型名）
    metadata: dict          # 其他元数据
```

### Trajectory

```python
class Trajectory(BaseModel):
    messages: List[Message]  # 对话消息列表
    score: float             # 轨迹评分（用于判断成功/失败）
    metadata: dict           # 可选的元数据（如segments、query等）
```

Task Memory通过分析Trajectory来提取经验。轨迹的score决定了它被分类为成功还是失败案例。

## Configuration Logic

Task Memory in ReMe is configured through two main flows:

### 1. Summary Task Memory

The `summary_task_memory` flow processes conversation trajectories to extract meaningful memories:

```yaml
summary_task_memory:
  flow_content: trajectory_preprocess_op >> (success_extraction_op|failure_extraction_op|comparative_extraction_op) >> memory_validation_op >> update_vector_store_op
  description: "Summarizes conversation trajectories or messages into structured memory representations for long-term storage"
```

This flow:
1. Preprocesses trajectories (`trajectory_preprocess_op`)
2. Extracts memories based on success/failure/comparative analysis
3. Validates memories (`memory_validation_op`)
4. Updates the vector store (`update_vector_store_op`)

A simplified version (`summary_task_memory_simple`) is also available for less complex use cases.

### 2. Retrieve Task Memory

The `retrieve_task_memory` flow fetches relevant memories based on a query:

```yaml
retrieve_task_memory:
  flow_content: build_query_op >> recall_vector_store_op >> rerank_memory_op >> rewrite_memory_op
  description: "Retrieves the most relevant top-k memory from historical data based on the current query to enhance task-solving capabilities"
```

This flow:
1. Builds a query from the input (`build_query_op`)
2. Recalls relevant memories from the vector store (`recall_vector_store_op`)
3. Reranks memories by relevance (`rerank_memory_op`)
4. Rewrites memories for better context integration (`rewrite_memory_op`)

A simplified version (`retrieve_task_memory_simple`) is also available.

## Basic Usage

Here's how to use Task Memory in your application:

### Step 1: Set Up Your Environment

```python
import requests

# API configuration
BASE_URL = "http://0.0.0.0:8002/"
WORKSPACE_ID = "your_workspace_id"
```

### Step 2: Run an Agent and Generate Memories

```python
# Run the agent with a query
response = requests.post(
    url=f"{BASE_URL}react",
    json={"query": "Your query here"}
)
messages = response.json().get("messages", [])

# Summarize the conversation to create task memories
response = requests.post(
    url=f"{BASE_URL}summary_task_memory",
    json={
        "workspace_id": WORKSPACE_ID,
        "trajectories": [
            {"messages": messages, "score": 1.0}
        ]
    }
)
```

### Step 3: Retrieve Relevant Memories for a New Task

```python
# Retrieve memories relevant to a new query
response = requests.post(
    url=f"{BASE_URL}retrieve_task_memory",
    json={
        "workspace_id": WORKSPACE_ID,
        "query": "Your new query here"
    }
)
retrieved_memory = response.json().get("answer", "")
```

### Step 4: Use Retrieved Memories to Enhance Agent Performance

```python
# Augment a new query with retrieved memories
augmented_query = f"{retrieved_memory}\n\nUser Question:\n{your_query}"

# Run agent with the augmented query
response = requests.post(
    url=f"{BASE_URL}react",
    json={"query": augmented_query}
)
```

## Complete Example

Here's a complete example workflow that demonstrates how to use task memory:

```python
def run_agent_with_memory(query_first, query_second):
    # Run agent with second query to build initial memories
    messages = run_agent(query=query_second)
    
    # Summarize conversation to create memories
    requests.post(
        url=f"{BASE_URL}summary_task_memory",
        json={
            "workspace_id": WORKSPACE_ID,
            "trajectories": [
                {"messages": messages, "score": 1.0}
            ]
        }
    )
    
    # Retrieve relevant memories for the first query
    response = requests.post(
        url=f"{BASE_URL}retrieve_task_memory",
        json={
            "workspace_id": WORKSPACE_ID,
            "query": query_first
        }
    )
    retrieved_memory = response.json().get("answer", "")
    
    # Run agent with first query augmented with retrieved memories
    augmented_query = f"{retrieved_memory}\n\nUser Question:\n{query_first}"
    return run_agent(query=augmented_query)
```

## Managing Task Memories

### Delete a Workspace

```python
response = requests.post(
    url=f"{BASE_URL}vector_store",
    json={
        "workspace_id": WORKSPACE_ID,
        "action": "delete"
    }
)
```

### Dump Memories to Disk

```python
response = requests.post(
    url=f"{BASE_URL}vector_store",
    json={
        "workspace_id": WORKSPACE_ID,
        "action": "dump",
        "path": "./"
    }
)
```

### Load Memories from Disk

```python
response = requests.post(
    url=f"{BASE_URL}vector_store",
    json={
        "workspace_id": WORKSPACE_ID,
        "action": "load",
        "path": "./"
    }
)
```

## Advanced Features

ReMe also provides additional task memory operations:

### Record Task Memory

`record_task_memory` flow用于更新检索到的任务记忆的使用频率和效用属性：

```yaml
record_task_memory:
  flow_content: update_memory_freq_op >> update_memory_utility_op >> update_vector_store_op
  description: "Update the freq & utility attributes of retrieved task memories"
  input_schema:
    workspace_id:
      type: string
      required: true
    memory_dicts:
      type: array
      description: "A list of retrieved task memory"
      required: true
    update_utility:
      type: boolean
      description: "Whether to update the utility attribute"
      required: true
```

使用示例：

```python
# 记录检索到的记忆被使用
response = requests.post(
    url=f"{BASE_URL}record_task_memory",
    json={
        "workspace_id": WORKSPACE_ID,
        "memory_dicts": retrieved_memories,  # 从retrieve_task_memory获取的记忆列表
        "update_utility": True  # 是否更新效用值
    }
)
```

### Delete Task Memory

`delete_task_memory` flow用于删除低效用的任务记忆：

```yaml
delete_task_memory:
  flow_content: delete_memory_op >> update_vector_store_op
  description: "Delete task memories when utility/freq < utility_threshold and freq >= freq_threshold"
  input_schema:
    workspace_id:
      type: string
      required: true
    freq_threshold:
      type: integer
      description: "The retrieved frequency threshold"
      required: true
    utility_threshold:
      type: number
      description: "The utility/freq threshold"
      required: true
```

使用示例：

```python
# 删除使用频率高但效用低的记忆
response = requests.post(
    url=f"{BASE_URL}delete_task_memory",
    json={
        "workspace_id": WORKSPACE_ID,
        "freq_threshold": 10,      # 至少被检索过10次
        "utility_threshold": 0.3   # 但效用/频率比 < 0.3
    }
)
```

这个机制确保记忆库的质量：频繁被检索但实际没什么帮助的记忆会被清理。

## 与Tool Memory的对比

| 特性 | Task Memory | Tool Memory |
|------|-------------|-------------|
| **目的** | 记录任务解决的经验 | 记录工具调用的使用模式 |
| **输入** | 对话轨迹（Trajectory） | 工具调用记录（ToolCallResult） |
| **索引方式** | when_to_use条件（语义搜索） | 工具名称（精确匹配） |
| **提取方式** | 从完整轨迹中分析提取 | 从单次调用评估和统计 |
| **内容** | 任务解决经验和策略 | 工具使用指南和最佳实践 |
| **更新方式** | 从成功/失败/对比中提取 | 每次调用后追加记录 |
| **检索流程** | 复杂：构建查询→召回→重排→重写 | 简单：精确匹配→返回 |
| **去重机制** | 语义去重（deduplication） | 按工具名唯一，限制历史条数 |
| **验证机制** | LLM验证质量（validation） | 评估单次调用质量 |

## 最佳实践

1. **轨迹评分标准**：
   - 明确定义成功和失败的评分标准
   - `success_threshold`通常设为1.0（完美成功）
   - 部分成功的轨迹（如0.5-0.9）可以提供对比经验

2. **轨迹质量**：
   - 确保轨迹包含完整的问题解决过程
   - 包含足够的上下文信息在metadata中
   - 避免过短或过长的轨迹

3. **定期维护**：
   - 使用`record_task_memory`跟踪记忆使用情况
   - 定期使用`delete_task_memory`清理低效记忆
   - 保持记忆库的质量和相关性

4. **合理使用简化版本**：
   - 简单场景使用`summary_task_memory_simple`
   - 复杂场景使用完整的`summary_task_memory` flow
   - 根据实际需求选择是否启用轨迹分割

5. **检索优化**：
   - 调整`top_k`参数（默认5）控制返回的记忆数量
   - 启用`enable_llm_rerank`提升相关性
   - 启用`enable_llm_rewrite`使记忆更适配当前任务

For more detailed examples, see the `use_task_memory_demo.py` file in the cookbook directory of the ReMe project.
