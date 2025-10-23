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


# Personal Memory

## Configuration Logic

ReMe's personal memory system consists of two main components: retrieval and summarization. The configuration for these components is defined in the default.yaml file.

### Retrieval Configuration (`retrieve_personal_memory`)

```yaml
retrieve_personal_memory:
  flow_content: set_query_op >> (extract_time_op | (retrieve_memory_op >> semantic_rank_op)) >> fuse_rerank_op
```

This flow performs the following operations:
1. `set_query_op`: Prepares the query for memory retrieval
2. Parallel paths:
   - `extract_time_op`: Extracts time-related information from the query
   - `retrieve_memory_op >> semantic_rank_op`: Retrieves memories and ranks them semantically
3. `fuse_rerank_op`: Combines and reranks the results for final output

### Summarization Configuration (`summary_personal_memory`)

```yaml
summary_personal_memory:
  flow_content: info_filter_op >> (get_observation_op | get_observation_with_time_op | load_today_memory_op) >> contra_repeat_op >> update_vector_store_op
```

This flow performs the following operations:
1. `info_filter_op`: Filters incoming information to extract relevant personal details
2. Parallel paths for observation extraction:
   - `get_observation_op`: Extracts general observations
   - `get_observation_with_time_op`: Extracts observations with time context
   - `load_today_memory_op`: Loads memories from the current day
3. `contra_repeat_op`: Removes contradictions and repetitions
4. `update_vector_store_op`: Stores the processed memories in the vector database

## Basic Usage

The following example demonstrates how to use personal memory in MemoryScope:

**1. Setup**

```{code-cell}
import asyncio
import json
import aiohttp

# API base URL (default is http://0.0.0.0:8002)
base_url = "http://0.0.0.0:8002"
workspace_id = "personal_memory_demo"
```

**2. Clear Existing Memories**

```{code-cell}
async with aiohttp.ClientSession() as session:
    # Delete existing workspace memories
    async with session.post(
        f"{base_url}/vector_store",
        json={
            "action": "delete",
            "workspace_id": workspace_id,
        },
        headers={"Content-Type": "application/json"}
    ) as response:
        result = await response.json()
```

**3. Create Conversation with Personal Information**

```{code-cell}
# Example conversation with personal details
messages = [
    {"role": "user", "content": "My name is John Smith, I'm 28 years old"},
    {"role": "assistant", "content": "Nice to meet you, John!"},
    {"role": "user", "content": "I'm a software engineer working with Python"},
    {"role": "assistant", "content": "I see, you're a Python engineer."},
    # Additional conversation messages...
]
```

**4. Summarize Personal Memories**

```{code-cell}
async with session.post(
    f"{base_url}/summary_personal_memory",
    json={
        "trajectories": [
            {"messages": messages, "score": 1.0}
        ],
        "workspace_id": workspace_id,
    },
    headers={"Content-Type": "application/json"}
) as response:
    result = await response.json()
```

**5. Retrieve Personal Memories**

```{code-cell}
# Example queries to retrieve personal information
queries = [
    "What's my name and age?",
    "What do I do for work?",
    "What are my hobbies?"
]

for query in queries:
    async with session.post(
        f"{base_url}/retrieve_personal_memory",
        json={
            "query": query,
            "workspace_id": workspace_id,
        },
        headers={"Content-Type": "application/json"}
    ) as response:
        result = await response.json()
        print(f"Query: {query}")
        print(f"Answer: {result.get('answer', '')}")
```

For a complete working example, refer to `/cookbook/simple_demo/use_personal_memory_demo.py` in the ReMe repository.