# Tool Summary Operations

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
- Analyzes the most recent N tool calls (configurable)
- Calculates statistical metrics (success rate, average scores, costs)
- Uses LLM to synthesize actionable usage guidelines
- Updates tool memory content with generated insights

### Parameters

- `op.summary_tool_memory_op.params.recent_call_count` (integer, default: `30`):
  - Number of most recent tool calls to analyze
  - Focuses on recent usage patterns

- `op.summary_tool_memory_op.params.summary_sleep_interval` (float, default: `1.0`):
  - Delay in seconds between concurrent summarizations
  - Prevents rate limiting when summarizing multiple tools

