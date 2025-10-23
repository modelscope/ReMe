---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Tool Memory Benchmark

## Overview

This benchmark evaluates Tool Memory effectiveness by comparing agent performance with and without tool memory across multiple epochs. The experiment uses mock search tools with varying performance characteristics for different query complexities.

## Experimental Setup

### Mock Search Tools

Three LLM-based mock search tools with different performance profiles:

| Tool | Simple Queries | Medium Queries | Complex Queries |
|------|---------------|----------------|-----------------|
| **SearchToolA** | ⭐⭐⭐ Fast, high success (90%) | ❌ Poor (20% success) | ⚠️ Weak (50% success) |
| **SearchToolB** | ⚠️ Over-engineered (30%) | ⭐⭐⭐ Optimal (90% success) | ⚠️ Limited (50% success) |
| **SearchToolC** | ⚠️ Overkill (30%) | ⚠️ Excessive (40%) | ⭐⭐⭐ Best (90% success) |

**Performance Characteristics:**
- `success_rate`: Probability of successful execution (vs "Service busy" error)
- `relevance_ratio`: Probability of returning relevant results (vs random content)
- `extra_time`: Simulated latency (currently 0 in implementation)

Each tool uses LLM to classify query complexity and generate appropriate responses.

### Query Dataset

**Source:** `cookbook/tool_memory/query.json`

- **Train Set**: 20 queries per complexity × 3 levels = 60 queries
- **Test Set**: 20 queries per complexity × 3 levels = 60 queries
- **Complexity Levels**: simple, moderate, complex

## Benchmark Workflow

### Single Epoch Process

Each epoch consists of 5 steps:

#### Step 1: Train without Memory
```{code-cell}
# Execute all train queries on TRAIN_WORKSPACE
# Agent selects tools without historical guidance
run_use_mock_search(TRAIN_WORKSPACE, train_queries, prompt_template)

# Add results to memory and get scored results
train_scored_results = add_tool_call_results(TRAIN_WORKSPACE, train_results)
```

#### Step 2: Test without Memory
```{code-cell}
# Execute all test queries on TEST_WORKSPACE (fresh workspace)
# Baseline performance without tool memory
run_use_mock_search(TEST_WORKSPACE, test_queries, prompt_template)

# Add results to memory (will be cleared in Step 4)
test_scored_results = add_tool_call_results(TEST_WORKSPACE, test_results)
```

#### Step 3: Summarize Tool Memory
```{code-cell}
# Summarize tool performance from TRAIN_WORKSPACE
summarize_tool_memory(TRAIN_WORKSPACE, "SearchToolA,SearchToolB,SearchToolC")

# Retrieve formatted tool memory content
memories = retrieve_tool_memory(TRAIN_WORKSPACE, tool_names)
```

The summarization produces memory content including:
- Best/worst use cases per tool
- Statistical metrics (avg score, success rate, token cost, time cost)
- Usage recommendations

#### Step 4: Test with Memory
```{code-cell}
# Clear TEST_WORKSPACE to start fresh
delete_workspace(TEST_WORKSPACE)

# Inject tool memory into prompt
prompt_with_memory = f"Tool Information\n{memories}\nMust select one tool to answer\nQuery\n{query}"

# Execute test queries with memory guidance
run_use_mock_search(TEST_WORKSPACE, test_queries, prompt_with_memory)

# Add results and get scored results
test_scored_results_with_memory = add_tool_call_results(TEST_WORKSPACE, test_results)
```

#### Step 5: Compare Results
```{code-cell}
# Generate comparison table
print_comparison_table([train_no_memory_stats, test_no_memory_stats, test_with_memory_stats])

# Calculate improvements (baseline: test without memory)
improvements = calculate_improvements(test_no_memory_stats, test_with_memory_stats)
print_improvements(improvements)
```

### Multi-Epoch Execution

```bash
# Run benchmark with 3 epochs
python cookbook/tool_memory/run_reme_tool_bench.py

# Test mode (5 queries per complexity level)
main(test_mode=True, run_epoch=3)

# Full mode (20 queries per complexity level)
main(test_mode=False, run_epoch=3)
```

## Key Components

### 1. Tool Selection: UseMockSearchOp

```{code-cell}
# Agent uses LLM to select appropriate tool
tool_call = await self.select_tool(query, [SearchToolA(), SearchToolB(), SearchToolC()])

# Execute selected tool and record results
result = ToolCallResult(
    create_time=timestamp,
    tool_name=tool_call.name,
    input={"query": query},
    output=content,
    token_cost=token_cost,
    success=success,
    time_cost=time_cost
)
```

### 2. Tool Call Result Evaluation

Results are automatically evaluated and scored:
- `score`: 0.0 (failure/irrelevant) or 1.0 (complete success)
- `success`: Tool execution status
- `summary`: Brief description
- `evaluation`: Detailed assessment

### 3. Tool Memory Schema

```{code-cell}
ToolMemory(
    workspace_id="workspace_id",
    memory_type="tool",
    when_to_use="Brief usage scenario description",
    content="Detailed performance analysis and recommendations",
    score=0.85,
    tool_call_results=[list of ToolCallResult],
    metadata={"tool_name": "SearchToolA"}
)
```

## Evaluation Metrics

### Per-Scenario Metrics
- **Avg Score**: Average quality score (0.0-1.0)
- **Total Calls**: Number of tool invocations
- **Success Rate**: Percentage of successful executions

### Improvement Calculation
```{code-cell}
improvement_percentage = ((with_memory_score - without_memory_score) / without_memory_score) * 100
```

## Expected Results

### Hypothesis
Tool Memory should enable the agent to:
1. **Select optimal tools** based on query complexity
2. **Improve average score** by 10-30% on test set
3. **Increase consistency** across multiple epochs

### Sample Output

```
==================================================================================================
BENCHMARK RESULTS COMPARISON
==================================================================================================
Note: Avg Score = average quality score
+---------------------------+--------------+-----------+
| Scenario                  | Total Calls  | Avg Score |
+===========================+==============+===========+
| Epoch1 - Train (No Memory)| 60           | 0.650     |
+---------------------------+--------------+-----------+
| Epoch1 - Test (No Memory) | 60           | 0.633     |
+---------------------------+--------------+-----------+
| Epoch1 - Test (With Memory)| 60          | 0.817     |
+---------------------------+--------------+-----------+

==================================================================================================
IMPROVEMENTS WITH TOOL MEMORY (Baseline: Test without memory)
==================================================================================================
Average Score            : +29.07% ↑
==================================================================================================
```

## Running the Benchmark

### Prerequisites
```bash
pip install requests python-dotenv loguru tabulate
```

### Start API Server
```bash
# Start ReMe API server
python reme_ai/app.py --port 8002
```

### Execute Benchmark
```bash
# Full benchmark (3 epochs, 60+60 queries per epoch)
python cookbook/tool_memory/run_reme_tool_bench.py

# Quick test (3 epochs, 15+15 queries per epoch)
# Modify main() call: main(test_mode=True, run_epoch=3)
```

### Output Files
- `tool_memory_benchmark_results.json`: Complete benchmark results
- Console output: Real-time progress and comparison tables

## API Endpoints Used

1. **`/use_mock_search`**: Execute tool selection and search
   - Input: `workspace_id`, `query`
   - Output: `ToolCallResult` JSON

2. **`/add_tool_call_result`**: Add results to memory and get evaluation scores
   - Input: `workspace_id`, `tool_call_results` (list)
   - Output: `memory_list` with scored results

3. **`/summary_tool_memory`**: Summarize tool performance
   - Input: `workspace_id`, `tool_names` (comma-separated)
   - Output: Updated `ToolMemory` with content

4. **`/retrieve_tool_memory`**: Retrieve formatted tool memory
   - Input: `workspace_id`, `tool_names`
   - Output: Markdown-formatted memory content

5. **`/vector_store`**: Delete workspace
   - Input: `workspace_id`, `action: "delete"`

## Concurrency Control

- **Max workers**: 4 parallel queries
- **Rate limiting**: 1 second delay between submissions
- **Timeout**: 120 seconds per API call

## References

- Tool Memory Schema: `reme_ai/schema/memory.py`
- Mock Tools Implementation: `reme_ai/agent/tools/mock_search_tools.py`
- LLM-based Search Op: `reme_ai/agent/tools/llm_mock_search_op.py`
- Tool Selection Op: `reme_ai/agent/tools/use_mock_search_op.py`
