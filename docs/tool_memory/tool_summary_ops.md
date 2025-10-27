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

# Tool Memory Summary Ops

## ParseToolCallResultOp

### Purpose

Evaluates individual tool invocations and adds them to the tool memory database with comprehensive assessments.

### Functionality

- Receives tool call results with input parameters, output, and metadata
- Uses LLM to evaluate each tool call based on success and parameter alignment
- Generates summary, evaluation, and score (0.0 or 1.0) for each call
- Appends evaluated results to existing tool memory or creates new memory
- Maintains a sliding window of recent tool calls (configurable limit)

### Parameters

- `op.parse_tool_call_result_op.params.max_history_tool_call_cnt` (integer, default: `100`):
  - Maximum number of historical tool call results to retain per tool
  - When exceeded, oldest results are removed (FIFO)

- `op.parse_tool_call_result_op.params.evaluation_sleep_interval` (float, default: `1.0`):
  - Delay in seconds between concurrent evaluations
  - Prevents rate limiting when evaluating multiple calls

## SummaryToolMemoryOp

### Purpose

Analyzes accumulated tool call history and generates comprehensive usage patterns, best practices, and recommendations.

### Functionality

- Retrieves existing tool memories from the vector store
- **Intelligently skips tools** where all recent calls have already been summarized (using `is_summarized` flag)
- Analyzes the most recent N tool calls (configurable)
- Calculates statistical metrics (success rate, average scores, costs)
- Uses LLM to synthesize actionable usage guidelines
- Updates tool memory content with generated insights
- **Marks processed calls** as summarized to avoid redundant processing in future runs

### Smart Skip Logic

To optimize costs and performance, `SummaryToolMemoryOp` tracks which tool call results have been included in a summary:

- **Skip Condition**: If all recent N calls are already summarized (`is_summarized=True`), the tool is skipped entirely
- **Trigger Condition**: If at least 1 recent call is new (`is_summarized=False`), re-summarization is triggered
- **Automatic Marking**: After successful summarization, all processed calls are marked with `is_summarized=True`

**Example Behavior**:
```
Run 1: 30 new calls → Summarize all 30, mark as summarized
Run 2: Same 30 calls → Skip (all already summarized) ✓ Cost savings
Run 3: 30 old + 1 new → Re-summarize all 31, mark new call as summarized
```

This ensures summaries stay fresh while avoiding unnecessary LLM calls.

### Parameters

- `op.summary_tool_memory_op.params.recent_call_count` (integer, default: `30`):
  - Number of most recent tool calls to analyze
  - Also determines the window for checking summarization status
  - Focuses on recent usage patterns

- `op.summary_tool_memory_op.params.summary_sleep_interval` (float, default: `1.0`):
  - Delay in seconds between concurrent summarizations
  - Prevents rate limiting when summarizing multiple tools

### Return Value

The operation returns a response message indicating:
- Number of tools summarized (had new unsummarized calls)
- Number of tools skipped (all recent calls already summarized)

Example: `"Successfully processed 5 tool memories: 2 summarized, 3 skipped (already up-to-date)"`


