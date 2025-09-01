# SOP Memory: Combining Atomic Operations into Complex Workflows

## 1. Background

In LLM application development, we often need to combine multiple basic operations (atomic operations) into more complex
workflows. These workflows can handle complex tasks such as data retrieval, code generation, multi-turn dialogues, and
more. By combining these atomic operations into Standard Operating Procedures (SOPs), we can:

- Improve code reusability
- Simplify implementation of complex tasks
- Standardize common workflows
- Reduce development and maintenance costs

This document introduces how to combine atomic operations (Ops) to form new composite operation tools using the FlowLLM
framework.

## 2. Technical Solution

### 2.1 Atomic Operation Definition

Each operation (Op) needs to define the following core attributes:

```python
class BaseOp:
    description: str  # Description of the operation
    input_schema: Dict[str, ParamAttr]  # Input parameter schema definition
    output_schema: Dict[str, ParamAttr]  # Output parameter schema definition
```

Where `ParamAttr` defines parameter type, whether it's required, and other attributes:

```python
class ParamAttr:
    type: Type  # Parameter type, such as str, int, Dict, etc.
    required: bool = True  # Whether it must be provided
    default: Any = None  # Default value
    description: str = ""  # Parameter description
```

### 2.2 SOP Composition Process

#### Step 1: Create Atomic Operation Instances

First, instantiate the required atomic operations:

```python
from flowllm.op.gallery.mock_op import MockOp
from flowllm.op.search.tavily_search_op import TavilySearchOp
from flowllm.op.agent.react_v2_op import ReactV2Op

# Create atomic operation instances
search_op = TavilySearchOp()
react_op = ReactV2Op()
summary_op = MockOp(
    description="Summarize search results",
    input_schema={"search_results": ParamAttr(type=str, description="Search results to summarize")},
    output_schema={"summary": ParamAttr(type=str, description="Summarized content")}
)
```

#### Step 2: Define Data Flow Between Operations

Set up input-output relationships between operations, defining how data flows between them:

```python
# Set input parameter sources
react_op.set_input("context",
                   "search_summary")  # react_op's context parameter is retrieved from search_summary in memory

# Set output parameter destinations
search_op.set_output("results", "search_results")  # search_op's results output to search_results in memory
summary_op.set_output("summary", "search_summary")  # summary_op's summary output to search_summary in memory
```

#### Step 3: Build Operation Flow Graph

Use operators to build the operation flow graph, defining execution order and parallel relationships:

```python
# Build operation flow graph
flow = search_op >> summary_op >> react_op

# Or more complex flows
# Parallel operations use the | operator, sequential operations use the >> operator
complex_flow = (search_op >> summary_op) | (another_search_op >> another_summary_op) >> react_op
```

Operator explanation:

- `>>`: Sequential execution, execute the next operation after the previous one completes
- `|`: Parallel execution, execute multiple operations simultaneously

#### Step 4: Create Composite Operation Class

Encapsulate the built operation flow into a new composite operation class:

```python
from flowllm.op.base_op import BaseOp


class SearchAndReactOp(BaseOp):
    description = "Search for information and generate a response based on search results"
    input_schema = ...
    output_schema = ...

    def build_flow(self):
        search_op = TavilySearchOp()
        summary_op = MockOp()
        react_op = ReactV2Op()

        # Set data flow
        search_op.set_output("results", "search_results")
        summary_op.set_input("search_results", "search_results")
        summary_op.set_output("summary", "search_summary")
        react_op.set_input("context", "search_summary")
        react_op.set_output("response", "response")

        # Build operation flow graph
        self.flow = search_op >> summary_op >> react_op

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Execute operation flow
        return await self.flow.execute(inputs)
```

### 2.3 Memory Management

Data transfer between operations is accomplished through memory space:

```python
# Memory space is a key-value store
memory = {}

# set_input reads data from memory
op.set_input("param_name", "memory_key")  # op.param_name = memory["memory_key"]

# set_output writes data to memory
op.set_output("result_name", "memory_key")  # memory["memory_key"] = op.result_name
```

## 3. Example: Building a Search Q&A SOP

Below is a complete example demonstrating how to build a search Q&A SOP:

```python
from flowllm.op.base_op import BaseOp
from flowllm.op.search.tavily_search_op import TavilySearchOp
from flowllm.op.agent.react_v2_op import ReactV2Op
from flowllm.schema.vector_node import ParamAttr


class SearchQAOp(BaseOp):
    description = "Search for information and answer questions based on search results"
    input_schema = {
        "question": ParamAttr(type=str, description="User question")
    }
    output_schema = {
        "answer": ParamAttr(type=str, description="Answer based on search results")
    }

    def __init__(self):
        super().__init__()

        # 1. Create atomic operation instances
        search_op = TavilySearchOp()
        react_op = ReactV2Op()

        # 2. Set data flow
        search_op.set_input("query", "question")  # Get search query from input question
        search_op.set_output("results", "search_results")  # Store search results in search_results

        react_op.set_input("question", "question")  # Get question from input question
        react_op.set_input("context", "search_results")  # Get context from search_results
        react_op.set_output("answer", "answer")  # Store answer in answer

        # 3. Build operation flow graph
        self.flow = search_op >> react_op

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return await self.flow.execute(inputs)
```

## 4. Solution Validation

### 4.1 Unit Testing

To verify the correctness of SOPs, we can write unit tests:

```python
import unittest
import asyncio
from flowllm.op.gallery.mock_op import MockOp
from flowllm.schema.vector_node import ParamAttr


class TestSOPMemory(unittest.TestCase):
    def test_simple_flow(self):
        # Create mock operations
        mock1 = MockOp(
            description="Mock operation 1",
            input_schema={"input1": ParamAttr(type=str)},
            output_schema={"output1": ParamAttr(type=str)}
        )
        mock2 = MockOp(
            description="Mock operation 2",
            input_schema={"input2": ParamAttr(type=str)},
            output_schema={"output2": ParamAttr(type=str)}
        )

        # Set data flow
        mock1.set_output("output1", "intermediate")
        mock2.set_input("input2", "intermediate")

        # Build flow
        flow = mock1 >> mock2

        # Execute flow
        result = asyncio.run(flow.execute({"input1": "test input"}))

        # Verify results
        self.assertIn("output2", result)
```

### 4.2 Integration Testing

Validate the effectiveness of SOPs through real-world scenario testing:

```python
async def test_search_qa():
    # Create SearchQA operation
    search_qa = SearchQAOp()

    # Execute operation
    result = await search_qa.execute({
        "question": "What is the capital of France?"
    })

    # Print results
    print(f"Question: What is the capital of France?")
    print(f"Answer: {result['answer']}")


# Run test
if __name__ == "__main__":
    asyncio.run(test_search_qa())
```

### 4.3 Performance Benchmarking

Measure SOP performance metrics:

```python
import time
import asyncio
from flowllm.utils.timer import Timer


async def benchmark_sop(sop_op, inputs, num_runs=10):
    total_time = 0
    results = []

    for _ in range(num_runs):
        with Timer() as timer:
            result = await sop_op.execute(inputs)

        total_time += timer.elapsed_time
        results.append(result)

    avg_time = total_time / num_runs
    print(f"Average execution time: {avg_time:.2f}s")

    return results, avg_time


# Run benchmark
search_qa = SearchQAOp()
asyncio.run(benchmark_sop(search_qa, {"question": "What is quantum computing?"}))
```

## 5. Best Practices

### 5.1 Operation Design Principles

- **Single Responsibility**: Each atomic operation should focus on a single functionality
- **Clear Interfaces**: Clearly define input and output schemas
- **Composability**: Design operations with combination with other operations in mind
- **Error Handling**: Properly handle exceptional cases

### 5.2 SOP Design Patterns

- **Pipeline Pattern**: `op1 >> op2 >> op3`
- **Branch Pattern**: `op1 >> (op2 | op3) >> op4`
- **Aggregation Pattern**: `(op1 | op2) >> op3`
- **Conditional Pattern**: Choose different operation paths based on conditions

### 5.3 Debugging Tips

- Use logging to record the input and output of each operation
- Create visualization charts for complex SOPs
- Use mock operations for isolated testing

## 6. Conclusion

Through the SOP Memory mechanism, we can flexibly combine atomic operations to build complex LLM application workflows.
This approach not only improves code maintainability and reusability but also makes the implementation of complex tasks
simpler and more standardized.

As more atomic operations are developed and refined, we can build a richer and more powerful SOP library, further
enhancing the development efficiency and quality of LLM applications.