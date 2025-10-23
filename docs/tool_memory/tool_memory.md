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

# Tool Memory

## 1. Background: Why Tool Memory?

### The MCP Tool Selection Challenge

In modern AI agent systems, LLMs face a rapidly expanding ecosystem of MCP (Model Context Protocol) tools. With hundreds or thousands of available tools, a critical problem emerges:

**The Core Problem: Tool Description is Not Enough**

When an LLM faces numerous MCP tools, it relies heavily on tool descriptions to decide which tool to use and how to use it. However:

- **Ambiguous Descriptions**: Many tools have similar descriptions but different performance characteristics
- **Hidden Complexity**: Static descriptions can't capture runtime behaviors, edge cases, or failure patterns
- **Parameter Confusion**: Tools may accept similar parameters with different optimal values
- **No Quality Signal**: Descriptions don't tell you which tools are reliable, fast, or cost-effective

**Example: Web Search Tools**

Imagine an LLM choosing between three search tools:
```
Tool A: "Search the web for information"
Tool B: "Perform web searches with customizable parameters"  
Tool C: "Query search engines and return results"
```

The descriptions are nearly identical, but in reality:
- Tool A: 95% success rate, avg 2.3s, best for technical queries
- Tool B: 70% success rate, avg 5.8s, often times out with >20 results
- Tool C: 85% success rate, avg 3.1s, good for general queries

**Without historical data, the LLM can't make informed decisions.**

### The Solution: Tool Memory as Context Enhancement

Tool Memory solves this by providing **learned context from historical usage**, transforming static tool descriptions into dynamic, data-driven guidance:

**1. Rule-Based Statistics** (Objective Metrics)
- **Success Rate**: "This tool succeeds 92% of the time"
- **Performance**: "Average execution time: 2.3s, token cost: 150"
- **Usage Patterns**: "Most successful calls use max_results=10-20"

**2. LLM-as-Judge Evaluation** (Qualitative Insights)
- **Quality Assessment**: LLM evaluates each call's effectiveness
- **Pattern Recognition**: Identifies why some calls succeed and others fail
- **Actionable Recommendations**: Synthesizes guidelines from patterns

**3. Enhanced Context for LLM Decision-Making**

Instead of just a tool description, the LLM now receives:

```
Tool: web_search

Static Description:
"Search the web for information"

+ Tool Memory Context:
"Based on 150 historical calls:
- Success rate: 92% (138 successful, 12 failed)
- Avg time: 2.3s, Avg tokens: 150
- Best for: Technical documentation, tutorials (95% success)
- Optimal params: max_results=5-20, language='en'
- Common failures: Generic queries timeout, max_results>50 unreliable
- Recommendation: Use specific multi-word queries with filter_type='technical_docs'"
```

This enriched context enables the LLM to:
- **Choose the right tool** based on task requirements and reliability
- **Use optimal parameters** learned from successful historical calls
- **Avoid known pitfalls** that caused previous failures
- **Estimate costs** (time and tokens) before execution

### The Impact: From Static Descriptions to Dynamic Intelligence

**Traditional Approach (Static Descriptions Only):**
```
LLM: "I have 50 search tools, all with similar descriptions"
→ Random choice or first match
→ Trial-and-error parameter selection
→ 75% success rate, repeated failures
```

**Tool Memory Approach (Description + Historical Context):**
```
LLM: "I have 50 search tools, but Tool A has 95% success for technical queries"
→ Informed choice based on data
→ Use proven parameter configurations
→ 92% success rate, optimized performance
```

**Real-World Impact:**

```
Before Tool Memory:
- Success rate: 75%
- Average time cost: 5.2s  
- Token cost: 200+ per call
- Repeated parameter errors
- Random tool selection

After Tool Memory:
- Success rate: 92% (+17%)
- Average time cost: 2.8s (-46%)
- Token cost: 150 per call (-25%)
- Consistent best practices
- Data-driven tool selection
```

### Why This Matters for MCP Ecosystem

As the MCP ecosystem grows, Tool Memory becomes essential:

1. **Scalability**: LLMs can navigate thousands of tools with confidence
2. **Quality Control**: Tools with poor performance get flagged automatically
3. **Continuous Improvement**: Every call improves the knowledge base
4. **Transfer Learning**: Insights from one agent benefit all agents in the workspace

**Tool Memory transforms tool descriptions from static documentation into living, learned manuals that improve with every use.**

## 2. What is Tool Memory?

Tool Memory is a structured knowledge base that captures insights from tool usage history. Each Tool Memory represents accumulated wisdom about a specific tool.

### Data Structure

#### ToolMemory

`ToolMemory` is the core data structure that stores comprehensive information about a tool's usage patterns:

```{code-cell}
class ToolMemory(BaseMemory):
    memory_type: str = "tool"                    # Type identifier
    workspace_id: str                            # Workspace identifier
    memory_id: str                               # Unique memory ID
    when_to_use: str                             # Tool name (serves as unique identifier)
    content: str                                 # Synthesized usage guidelines
    score: float                                 # Overall quality score
    time_created: str                            # Creation timestamp
    time_modified: str                           # Last modification timestamp
    author: str                                  # Creator (typically LLM model name)
    tool_call_results: List[ToolCallResult]      # Historical invocation records
    metadata: dict                               # Additional metadata
```

**Key Fields:**
- **`when_to_use`**: The tool name, used as the unique identifier for retrieval
- **`content`**: Human-readable usage guidelines synthesized from historical data
- **`tool_call_results`**: Complete history of tool invocations with evaluations
- **`score`**: Overall quality metric for the tool's performance

#### ToolCallResult

Each tool invocation is captured as a `ToolCallResult`:

```{code-cell}
class ToolCallResult(BaseModel):
    create_time: str        # Invocation timestamp
    tool_name: str          # Name of the tool
    input: dict | str       # Input parameters
    output: str             # Tool output
    token_cost: int         # Token consumption
    success: bool           # Whether invocation succeeded
    time_cost: float        # Time consumed (seconds)
    summary: str            # Brief summary of the result
    evaluation: str         # Detailed evaluation (generated by LLM)
    score: float            # Evaluation score (0.0 for failure, 1.0 for success)
    metadata: dict          # Additional metadata
```

**Key Fields:**
- **`input`/`output`**: The complete I/O data for analysis
- **`summary`**: LLM-generated brief summary of what happened
- **`evaluation`**: LLM-generated detailed analysis of the call quality
- **`score`**: Binary evaluation (0.0 = failure, 1.0 = success)
- **Performance metrics**: `time_cost`, `token_cost`, `success` for statistical analysis

### Tool Memory Lifecycle

```{mermaid}
graph LR
    A[Tool Call] --> B[Evaluate]
    B --> C[Store Memory]
    C --> D[(Vector Store)]
    D --> E[Agent Retrieves]
    E --> A
    C -.Periodic.-> F[Summarize]
    F --> C
```

## 3. How Tool Memory Works: The Complete Flow

Tool Memory operates through three complementary operations that work together to create a learning loop:

```{mermaid}
graph LR
    A[Agent] -->|1 retrieve_tool_memory| B[(Vector Store)]
    B -->|Guidelines| A
    A -->|2 Execute Tool| C[Tool]
    C -->|Result| A
    A -->|3 add_tool_call_result| D[LLM Evaluate]
    D -->|Store| B
    B -->|Periodic| E[summary_tool_memory]
    E -->|4 Update Guidelines| B
```

### Operation Flow

**1. retrieve_tool_memory** (Before Execution)
- Agent queries: "How should I use `web_search` tool?"
- Retrieves stored guidelines and historical patterns
- Returns: Usage recommendations, parameter suggestions, common pitfalls

**2. Tool Execution**
- Agent executes tool with informed parameters
- Collects: input, output, time_cost, token_cost, success status

**3. add_tool_call_result** (After Execution)
- Submits execution data for evaluation
- LLM analyzes: Was it successful? What could be improved?
- Generates: summary, evaluation, score (0.0 or 1.0)
- Appends to tool's historical record in Vector Store

**4. summary_tool_memory** (Periodic)
- Analyzes recent N tool calls (e.g., last 20-30)
- Calculates statistics: success rate, avg costs, avg score
- LLM synthesizes: Actionable usage guidelines
- Updates the `content` field with comprehensive guidance

### Example Flow from Demo

Based on `use_tool_memory_demo.py`, here's a typical workflow:

```{code-cell}
# Step 1: Add tool call results (accumulate history)
add_tool_call_results([
    {"tool_name": "web_search", "input": {...}, "output": "...", "success": True},
    {"tool_name": "web_search", "input": {...}, "output": "...", "success": False},
    # ... more results
])

# Step 2: Generate usage guidelines (periodic)
summarize_tool_memory("web_search")

# Step 3: Retrieve guidelines before next use
memory = retrieve_tool_memory("web_search")
# Returns:
# "For web_search tool:
#  - Use max_results=5-20 for optimal performance
#  - Avoid generic queries, be specific
#  - Language parameter 'en' has 95% success rate
#  Statistics: 83% success, avg 2.3s, avg 150 tokens"

# Step 4: Agent uses guidelines for better execution
execute_with_recommended_parameters()
```

## 4. Operation Details: How to Use Each Component

### 4.1 `add_tool_call_result`

**Purpose**: Evaluate and store tool call results into Tool Memory.

**Flow**:
```yaml
add_tool_call_result:
  flow_content: parse_tool_call_result_op >> update_vector_store_op
  description: "Evaluates and adds tool call results to the tool memory database"
```

**Process**:
1. Receives raw tool call results
2. Uses LLM to evaluate each call (generates summary, evaluation, score)
3. Groups results by tool name
4. Creates or updates ToolMemory objects
5. Stores in Vector Store

**Configuration** (`default.yaml`):
```yaml
op:
  parse_tool_call_result_op:
    backend: parse_tool_call_result_op
    llm: default
    params:
      max_history_tool_call_cnt: 100      # Max calls to retain per tool
      evaluation_sleep_interval: 1.0      # Delay between evaluations (seconds)
```

#### Usage with curl

```bash
curl -X POST http://0.0.0.0:8002/add_tool_call_result \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "tool_call_results": [
      {
        "create_time": "2025-10-21 10:30:00",
        "tool_name": "web_search",
        "input": {
            "query": "Python asyncio tutorial",
            "max_results": 10,
            "language": "en"
        },
        "output": "Found 10 relevant results including official docs and tutorials",
        "token_cost": 150,
        "success": true,
        "time_cost": 2.3
      },
      {
        "create_time": "2025-10-21 10:32:00",
        "tool_name": "web_search",
        "input": {
          "query": "test",
          "max_results": 100,
          "language": "unknown"
        },
        "output": "Error: Invalid language parameter",
        "token_cost": 50,
        "success": false,
        "time_cost": 0.5
      }
    ]
  }'
```

**Response**:
```json
{
  "success": true,
  "answer": "Successfully evaluated and stored 2 tool call results",
  "metadata": {
    "memory_list": [
      {
        "when_to_use": "web_search",
        "memory_id": "abc123...",
        "tool_call_results": [
          {
            "tool_name": "web_search",
            "summary": "Successfully retrieved relevant Python asyncio documentation",
            "evaluation": "Good parameter choices with appropriate max_results and language settings",
            "score": 1.0,
            ...
          },
          {
            "tool_name": "web_search",
            "summary": "Failed due to invalid language parameter",
            "evaluation": "Query too generic and language parameter not supported",
            "score": 0.0,
            ...
          }
        ]
      }
    ]
  }
}
```

#### Usage with Python

```{code-cell}
import requests
from datetime import datetime

def add_tool_call_results(tool_call_results: list) -> dict:
    """Add tool call results to Tool Memory"""
    response = requests.post(
        url=f"{BASE_URL}add_tool_call_result",
        json={
            "workspace_id": WORKSPACE_ID,
            "tool_call_results": tool_call_results
        }
    )
    return response.json()

# Example: Record a tool invocation
result = add_tool_call_results([{
    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "tool_name": "web_search",
    "input": {"query": "Python asyncio", "max_results": 10},
    "output": "Found 10 relevant results...",
    "token_cost": 150,
    "success": True,
    "time_cost": 2.3
}])
```

**Complete examples**: See `cookbook/simple_demo/use_tool_memory_demo.py` for full working code.

---

### 4.2 `retrieve_tool_memory`

**Purpose**: Retrieve usage guidelines and historical data for specific tools.

**Flow**:
```yaml
retrieve_tool_memory:
  flow_content: retrieve_tool_memory_op
  description: "Retrieves tool memories from the vector database based on tool names"
```

**Process**:
1. Takes comma-separated tool names as input
2. Searches Vector Store for exact matches (by `when_to_use` field)
3. Returns complete ToolMemory objects with:
   - Usage guidelines (`content`)
   - Historical call records (`tool_call_results`)
   - Statistics and metadata

#### Usage with curl

```bash
# Retrieve single tool
curl -X POST http://0.0.0.0:8002/retrieve_tool_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "tool_names": "web_search"
  }'

# Retrieve multiple tools (comma-separated)
curl -X POST http://0.0.0.0:8002/retrieve_tool_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "tool_names": "web_search,database_query,file_processor"
  }'
```

**Response**:
```json
{
  "success": true,
  "answer": "Successfully retrieved 1 tool memories",
  "metadata": {
    "memory_list": [
      {
        "memory_type": "tool",
        "workspace_id": "my_workspace",
        "memory_id": "abc123...",
        "when_to_use": "web_search",
        "content": "## Usage Guidelines\n\n**Best Practices:**\n- Use max_results between 5-20 for optimal performance\n- Always specify language parameter (en has 95% success rate)\n- Avoid generic single-word queries\n\n**Common Pitfalls:**\n- max_results > 50 often causes timeouts\n- Unknown language values default to 'en' with warning\n\n## Statistics\n- **Success Rate**: 83.33%\n- **Average Score**: 0.833\n- **Average Time Cost**: 2.345s\n- **Average Token Cost**: 156.7",
        "score": 0.85,
        "time_created": "2025-10-20 10:00:00",
        "time_modified": "2025-10-21 10:35:00",
        "author": "gpt-4",
        "tool_call_results": [
          {
            "create_time": "2025-10-21 10:30:00",
            "tool_name": "web_search",
            "input": {"query": "Python asyncio", "max_results": 10},
            "output": "Found 10 results...",
            "summary": "Successfully retrieved relevant documentation",
            "evaluation": "Good parameter choices...",
            "score": 1.0,
            "token_cost": 150,
            "success": true,
            "time_cost": 2.3
          }
          // ... more historical calls
        ]
      }
    ]
  }
}
```

#### Usage with Python

```{code-cell}
import requests

def retrieve_tool_memory(tool_names: str) -> dict:
    """Retrieve tool memories by tool names"""
    response = requests.post(
        url=f"{BASE_URL}retrieve_tool_memory",
        json={
            "workspace_id": WORKSPACE_ID,
            "tool_names": tool_names
        }
    )
    return response.json()

# Example: Retrieve and use guidelines
result = retrieve_tool_memory("web_search")
if result['success']:
    memory = result['metadata']['memory_list'][0]
    print(f"Tool: {memory['when_to_use']}")
    print(f"Guidelines:\n{memory['content']}")
```

**Complete examples**: See `cookbook/simple_demo/use_tool_memory_demo.py` for full working code.

---

### 4.3 `summary_tool_memory`

**Purpose**: Analyze historical tool calls and generate comprehensive usage guidelines.

**Flow**:
```yaml
summary_tool_memory:
  flow_content: summary_tool_memory_op >> update_vector_store_op
  description: "Analyzes tool call history and generates comprehensive usage patterns"
```

**Process**:
1. Retrieves existing ToolMemory by tool name
2. Analyzes recent N tool calls (default: 30)
3. Calculates statistics:
   - Success rate
   - Average score
   - Average time cost
   - Average token cost
4. Uses LLM to synthesize actionable guidelines from call summaries
5. Appends statistics to guidelines
6. Updates ToolMemory content in Vector Store

**Configuration** (`default.yaml`):
```yaml
op:
  summary_tool_memory_op:
    backend: summary_tool_memory_op
    llm: default
    params:
      recent_call_count: 30               # Number of recent calls to analyze
      summary_sleep_interval: 1.0         # Delay between summaries (seconds)
```

#### Usage with curl

```bash
# Summarize single tool
curl -X POST http://0.0.0.0:8002/summary_tool_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "tool_names": "web_search"
  }'

# Summarize multiple tools (comma-separated)
curl -X POST http://0.0.0.0:8002/summary_tool_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "tool_names": "web_search,database_query,file_processor"
  }'
```

**Response**:
```json
{
  "success": true,
  "answer": "Successfully summarized 1 tool memories",
  "metadata": {
    "memory_list": [
      {
        "memory_type": "tool",
        "when_to_use": "web_search",
        "content": "## Usage Guidelines\n\n**Optimal Parameters:**\n- Set max_results between 5-20 for best balance of coverage and speed\n- Always specify language='en' for technical queries (95% success rate)\n- Use filter_type='technical_docs' for development-related searches\n\n**Success Patterns:**\n- Specific, multi-word queries perform significantly better than generic terms\n- Queries with clear intent (e.g., 'Python asyncio tutorial') return high-quality results\n- Technical terms and version numbers improve result relevance\n\n**Common Failures:**\n- Generic single-word queries (e.g., 'test') return poor results\n- max_results > 50 increases timeout risk (5 failures observed)\n- Invalid language codes cause fallback to default with warnings\n\n**Performance Insights:**\n- Typical response time: 1.5-3.5s for successful queries\n- Timeout threshold: 10s (consider simplifying complex queries)\n- Token cost scales with result count: ~150 tokens for 10 results\n\n**Recommendations:**\n1. Always validate language parameter before calling\n2. Start with max_results=10, adjust based on needs\n3. For time-sensitive operations, set timeout < 5s\n4. Monitor token costs for high-frequency usage\n\n## Statistics\n- **Success Rate**: 83.33%\n- **Average Score**: 0.833\n- **Average Time Cost**: 2.345s\n- **Average Token Cost**: 156.7",
        "memory_id": "abc123...",
        "time_modified": "2025-10-21 10:40:00",
        ...
      }
    ]
  }
}
```

#### Usage with Python

```{code-cell}
import requests

def summarize_tool_memory(tool_names: str) -> dict:
    """Generate comprehensive usage guidelines for tools"""
    response = requests.post(
        url=f"{BASE_URL}summary_tool_memory",
        json={
            "workspace_id": WORKSPACE_ID,
            "tool_names": tool_names
        }
    )
    return response.json()

# Example: Generate guidelines
result = summarize_tool_memory("web_search")
if result['success']:
    memory = result['metadata']['memory_list'][0]
    print(f"Tool: {memory['when_to_use']}")
    print(f"Guidelines:\n{memory['content']}")
```

**Complete examples**: See `cookbook/simple_demo/use_tool_memory_demo.py` for full working code.

---

## 5. Best Practices

### When to Record Tool Calls
- **Always**: Record every tool invocation, including failures
- **Include**: Complete input parameters, output, and performance metrics
- **Timing**: Record immediately after tool execution completes

### When to Generate Summaries
- **Initial**: After accumulating 20-30 tool calls for meaningful patterns
- **Periodic**: Re-summarize every 50-100 new calls or weekly
- **Trigger-based**: When success rate drops or patterns change significantly

### When to Retrieve Guidelines
- **Before first use**: Always retrieve before using an unfamiliar tool
- **Before critical operations**: Check latest guidelines for important tasks
- **After updates**: Re-retrieve when tool memory has been updated

### Performance Tuning

**For High-Volume Tools** (>100 calls/day):
```yaml
op:
  parse_tool_call_result_op:
    params:
      max_history_tool_call_cnt: 200      # Keep more history
      evaluation_sleep_interval: 0.5      # Faster evaluation
  
  summary_tool_memory_op:
    params:
      recent_call_count: 50               # Analyze more calls
```

**For Low-Volume Tools** (<20 calls/day):
```yaml
op:
  parse_tool_call_result_op:
    params:
      max_history_tool_call_cnt: 50       # Less history needed
      evaluation_sleep_interval: 1.0      # Standard rate
  
  summary_tool_memory_op:
    params:
      recent_call_count: 20               # Analyze fewer calls
```

### Quality Maintenance

1. **Monitor Metrics**:
```{code-cell}
   memory = retrieve_tool_memory("web_search")['metadata']['memory_list'][0]
   stats = ToolMemory(**memory).statistic(recent_frequency=30)
   
   print(f"Success Rate: {stats['success_rate']:.2%}")
   print(f"Avg Score: {stats['avg_score']:.2f}")
   
   if stats['success_rate'] < 0.7:
       print("⚠️ Low success rate - investigate tool issues")
   ```

2. **Clean Old Memories**:
   - Delete tool memories for deprecated tools
   - Reset memories when tool behavior changes significantly

3. **Validate Guidelines**:
   - Periodically review generated guidelines for accuracy
   - Test recommended parameters in production scenarios

## 6. Memory Management

### Delete Workspace
```bash
curl -X POST http://0.0.0.0:8002/vector_store \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "action": "delete"
  }'
```

```{code-cell}
def delete_workspace(workspace_id: str):
    response = requests.post(
        url=f"{BASE_URL}vector_store",
        json={"workspace_id": workspace_id, "action": "delete"}
    )
    return response.json()
```

### Dump Memories to Disk
```bash
curl -X POST http://0.0.0.0:8002/vector_store \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "action": "dump",
    "path": "./memory_backup/"
  }'
```

```{code-cell}
def dump_memory(workspace_id: str, path: str = "./"):
    response = requests.post(
        url=f"{BASE_URL}vector_store",
        json={"workspace_id": workspace_id, "action": "dump", "path": path}
    )
    return response.json()
```

### Load Memories from Disk
```bash
curl -X POST http://0.0.0.0:8002/vector_store \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "my_workspace",
    "action": "load",
    "path": "./memory_backup/"
  }'
```

```{code-cell}
def load_memory(workspace_id: str, path: str = "./"):
    response = requests.post(
        url=f"{BASE_URL}vector_store",
        json={"workspace_id": workspace_id, "action": "load", "path": path}
    )
    return response.json()
```

## 7. Complete Working Example

For a complete, runnable example demonstrating the full Tool Memory lifecycle, see:

**`cookbook/simple_demo/use_tool_memory_demo.py`**

This demo includes:
- **Workspace management**: Clean, delete, dump, and load operations
- **Tool call recording**: Adding 30+ mock tool invocations with various scenarios
- **Summarization**: Generating usage guidelines from historical data
- **Retrieval**: Fetching and displaying tool memories
- **Statistics**: Analyzing success rates, costs, and performance

Run the demo:
```bash
cd cookbook/simple_demo
python use_tool_memory_demo.py
```

**Key Workflow Steps:**
1. **Clean workspace**: Remove existing data
2. **Add tool calls**: Record 30+ invocations (success/failure scenarios)
3. **Generate guidelines**: LLM analyzes patterns and creates recommendations
4. **Retrieve memory**: Get usage guidelines for agent consumption
5. **Persistence**: Test dump/load operations

## 8. Advanced Use Cases

### Use Case 1: Adaptive Parameter Tuning

Retrieve tool memory statistics and adapt parameters based on historical performance:
- If `avg_time_cost > 5s`: Increase timeout
- If `success_rate < 80%`: Enable retry logic
- If `avg_token_cost` high: Reduce result limits

### Use Case 2: Multi-Tool Workflow Optimization

Retrieve memories for multiple tools at once and optimize workflow order based on:
- Success rates: Execute reliable tools first
- Time costs: Parallelize slow operations
- Token costs: Budget-aware tool selection

### Use Case 3: Automated Quality Monitoring

Periodically check tool memory statistics and alert on:
- Success rate degradation
- Increasing time/token costs
- Unusual failure patterns

**Implementation examples**: See `cookbook/simple_demo/use_tool_memory_demo.py` and the ToolBench evaluation scripts.

## 9. Benchmark Results

### Tool Memory Performance Evaluation

We evaluated Tool Memory effectiveness using a controlled benchmark with three mock search tools, each optimized for different query complexity levels (simple, moderate, complex). The benchmark compares agent performance with and without tool memory guidance across multiple epochs.

**Experimental Settings:**
- **Model**: Qwen3-30B-Instruct with default parameters
- **Task**: Single-turn tool selection and invocation
- **Dataset**: 60 training queries + 60 test queries per epoch
- **Tools**: 3 mock search tools with varying performance profiles
- **Metrics**: Average quality score (0.0-1.0) based on LLM evaluation
- **Baseline**: Test set performance without tool memory
- **Replication**: Results averaged across 3 independent experimental runs

**Results (averaged across 3 epochs):**

| Scenario | Avg Score | Improvement |
|----------|-----------|-------------|
| Train (No Memory) | 0.650 | - |
| Test (No Memory) | 0.672 | Baseline |
| **Test (With Memory)** | **0.772** | **+14.88%** |

**Key Findings:**
- **Consistent improvement**: Tool Memory boosted test performance by ~15% on average
- **Knowledge transfer**: Training data successfully informed test-time tool selection
- **Stability**: Improvement remained consistent across all 3 epochs (9.90% → 17.39% → 17.13%)

The benchmark demonstrates that Tool Memory enables agents to make data-driven tool selection decisions, significantly improving task success rates compared to relying solely on static tool descriptions.

**Benchmark Resources:**
- **Design Documentation**: [`docs/tool_memory/tool_bench.md`](tool_bench.md) - Complete benchmark methodology and workflow
- **Implementation**: [`cookbook/tool_memory/run_reme_tool_bench.py`](../../cookbook/tool_memory/run_reme_tool_bench.py) - Full benchmark script
- **Query Dataset**: [`cookbook/tool_memory/query.json`](../../cookbook/tool_memory/query.json) - 60 train + 60 test queries across 3 complexity levels

---

## 10. References

- **Implementation**: See `reme_ai/summary/tool/` and `reme_ai/retrieve/tool/`
- **Demo**: `cookbook/simple_demo/use_tool_memory_demo.py`
- **Benchmark**: `cookbook/tool_memory/run_reme_tool_bench.py`
- **Schema**: `reme_ai/schema/memory.py`
- **Utilities**: `reme_ai/utils/tool_memory_utils.py`
