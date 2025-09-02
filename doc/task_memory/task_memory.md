# Task Memory in Reme

Task Memory is a key component of Reme that allows AI agents to learn from past experiences and improve their performance on similar tasks in the future. This document explains how task memory works and how to use it in your applications.

## What is Task Memory?

Task Memory represents knowledge extracted from previous task executions, including:
- Successful approaches to solving problems
- Common pitfalls and failures to avoid
- Comparative insights between different approaches

Each task memory contains:
- `when_to_use`: Conditions that indicate when this memory is relevant
- `content`: The actual knowledge or experience to be applied
- Metadata about the memory's source and utility

## Configuration Logic

Task Memory in Reme is configured through two main flows:

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
  description: "Retrieves the most relevant top-k memory experiences from historical data based on the current query to enhance task-solving capabilities"
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

Reme also provides additional task memory operations:

- `record_task_memory`: Update frequency and utility attributes of retrieved memories
- `delete_task_memory`: Delete memories based on utility/frequency thresholds

For more detailed examples, see the `use_task_memory_demo.py` file in the cookbook directory of the Reme project.
