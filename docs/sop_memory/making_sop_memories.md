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

```{code-cell}
class BaseAsyncToolOp:
    description: str  # Description of the operation
    input_schema: Dict[str, ParamAttr]  # Input parameter schema definition
    output_schema: Dict[str, ParamAttr]  # Output parameter schema definition
```

Where `ParamAttr` defines parameter type, whether it's required, and other attributes:

```{code-cell}
class ParamAttr:
    type: Type  # Parameter type, such as str, int, Dict, etc.
    required: bool = True  # Whether it must be provided
    default: Any = None  # Default value
    description: str = ""  # Parameter description
```

### 2.2 SOP Composition Process

#### Step 1: Create Atomic Operation Instances

First, instantiate the required atomic operations:

```{code-cell}
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

```{code-cell}
# Set input parameter sources
react_op.set_input("context",
                   "search_summary")  # react_op's context parameter is retrieved from search_summary in memory

# Set output parameter destinations
search_op.set_output("results", "search_results")  # search_op's results output to search_results in memory
summary_op.set_output("summary", "search_summary")  # summary_op's summary output to search_summary in memory
```

#### Step 3: Build Operation Flow Graph

Use operators to build the operation flow graph, defining execution order and parallel relationships:

```{code-cell}
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

```{code-cell}

class SearchAndReactOp(BaseToolOp):
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
        return search_op >> summary_op >> react_op

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Execute operation flow
        return await self.flow.execute(inputs)
```