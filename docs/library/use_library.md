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

# Use Library

ReMe provides pre-built memory libraries that agents can immediately use with verified best practices:

### Available Libraries

- **`appworld.jsonl`**: Memory library for Appworld agent interactions, covering complex task planning and execution
  patterns
- **`bfcl_v3.jsonl`**: Working memory library for BFCL tool calls

### Quick Usage

Load pre-built memories:

```{code-cell}
response = requests.post("http://localhost:8002/vector_store", json={
    "workspace_id": "appworld",
    "action": "load",
    "path": "./docs/library/"
})

# Query relevant memories
response = requests.post("http://localhost:8002/retrieve_task_memory", json={
    "workspace_id": "appworld",
    "query": "How to navigate to settings and update user profile?",
    "top_k": 1
})
```
