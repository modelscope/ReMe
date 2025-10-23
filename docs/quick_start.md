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

# Quick Start

### HTTP Service Startup

```bash
reme \
  backend=http \
  http.port=8002 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

### MCP Server Support

```bash
reme \
  backend=mcp \
  mcp.transport=stdio \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local
```

### Core API Usage

#### Task Memory Management

```{code-cell}
import requests

# Experience Summarizer: Learn from execution trajectories
response = requests.post("http://localhost:8002/summary_task_memory", json={
    "workspace_id": "task_workspace",
    "trajectories": [
        {"messages": [{"role": "user", "content": "Help me create a project plan"}], "score": 1.0}
    ]
})

# Retriever: Get relevant memories
response = requests.post("http://localhost:8002/retrieve_task_memory", json={
    "workspace_id": "task_workspace",
    "query": "How to efficiently manage project progress?",
    "top_k": 1
})
```


````{dropdown} curl version
```bash
# Experience Summarizer: Learn from execution trajectories
curl -X POST http://localhost:8002/summary_task_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "task_workspace",
    "trajectories": [
      {"messages": [{"role": "user", "content": "Help me create a project plan"}], "score": 1.0}
    ]
  }'

# Retriever: Get relevant memories
curl -X POST http://localhost:8002/retrieve_task_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "task_workspace",
    "query": "How to efficiently manage project progress?",
    "top_k": 1
  }'
```
````

````{dropdown} Node.js version
```{code-block} javascript
// Experience Summarizer: Learn from execution trajectories
fetch("http://localhost:8002/summary_task_memory", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "task_workspace",
    trajectories: [
      {messages: [{role: "user", content: "Help me create a project plan"}], score: 1.0}
    ]
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Retriever: Get relevant memories
fetch("http://localhost:8002/retrieve_task_memory", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "task_workspace",
    query: "How to efficiently manage project progress?",
    top_k: 1
  })
})
.then(response => response.json())
.then(data => console.log(data));
```
````

#### Personal Memory Management

```{code-cell}
# Memory Integration: Learn from user interactions
response = requests.post("http://localhost:8002/summary_personal_memory", json={
    "workspace_id": "task_workspace",
    "trajectories": [
        {"messages":
            [
                {"role": "user", "content": "I like to drink coffee while working in the morning"},
                {"role": "assistant",
                 "content": "I understand, you prefer to start your workday with coffee to stay energized"}
            ]
        }
    ]
})

# Memory Retrieval: Get personal memory fragments
response = requests.post("http://localhost:8002/retrieve_personal_memory", json={
    "workspace_id": "task_workspace",
    "query": "What are the user's work habits?",
    "top_k": 5
})
```

````{dropdown} curl version

```bash
# Memory Integration: Learn from user interactions
curl -X POST http://localhost:8002/summary_personal_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "task_workspace",
    "trajectories": [
      {"messages": [
        {"role": "user", "content": "I like to drink coffee while working in the morning"},
        {"role": "assistant", "content": "I understand, you prefer to start your workday with coffee to stay energized"}
      ]}
    ]
  }'

# Memory Retrieval: Get personal memory fragments
curl -X POST http://localhost:8002/retrieve_personal_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "task_workspace",
    "query": "What are the user's work habits?",
    "top_k": 5
  }'
```
````

````{dropdown} Node.js version

```{code-block} javascript
// Memory Integration: Learn from user interactions
fetch("http://localhost:8002/summary_personal_memory", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "task_workspace",
    trajectories: [
      {messages: [
        {role: "user", content: "I like to drink coffee while working in the morning"},
        {role: "assistant", content: "I understand, you prefer to start your workday with coffee to stay energized"}
      ]}
    ]
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Memory Retrieval: Get personal memory fragments
fetch("http://localhost:8002/retrieve_personal_memory", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "task_workspace",
    query: "What are the user's work habits?",
    top_k: 5
  })
})
.then(response => response.json())
.then(data => console.log(data));
```
````


#### Tool Memory Management

```{code-cell}
import requests

# Record tool execution results
response = requests.post("http://localhost:8002/add_tool_call_result", json={
    "workspace_id": "tool_workspace",
    "tool_call_results": [
        {
            "create_time": "2025-10-21 10:30:00",
            "tool_name": "web_search",
            "input": {"query": "Python asyncio tutorial", "max_results": 10},
            "output": "Found 10 relevant results...",
            "token_cost": 150,
            "success": True,
            "time_cost": 2.3
        }
    ]
})

# Generate usage guidelines from history
response = requests.post("http://localhost:8002/summary_tool_memory", json={
    "workspace_id": "tool_workspace",
    "tool_names": "web_search"
})

# Retrieve tool guidelines before use
response = requests.post("http://localhost:8002/retrieve_tool_memory", json={
    "workspace_id": "tool_workspace",
    "tool_names": "web_search"
})
```


````{dropdown} curl version

```bash
# Record tool execution results
curl -X POST http://localhost:8002/add_tool_call_result \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "tool_workspace",
    "tool_call_results": [
      {
        "create_time": "2025-10-21 10:30:00",
        "tool_name": "web_search",
        "input": {"query": "Python asyncio tutorial", "max_results": 10},
        "output": "Found 10 relevant results...",
        "token_cost": 150,
        "success": true,
        "time_cost": 2.3
      }
    ]
  }'

# Generate usage guidelines from history
curl -X POST http://localhost:8002/summary_tool_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "tool_workspace",
    "tool_names": "web_search"
  }'

# Retrieve tool guidelines before use
curl -X POST http://localhost:8002/retrieve_tool_memory \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "tool_workspace",
    "tool_names": "web_search"
  }'
```
````

````{dropdown} Node.js version

```{code-block} javascript
// Record tool execution results
fetch("http://localhost:8002/add_tool_call_result", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "tool_workspace",
    tool_call_results: [
      {
        create_time: "2025-10-21 10:30:00",
        tool_name: "web_search",
        input: {query: "Python asyncio tutorial", max_results: 10},
        output: "Found 10 relevant results...",
        token_cost: 150,
        success: true,
        time_cost: 2.3
      }
    ]
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Generate usage guidelines from history
fetch("http://localhost:8002/summary_tool_memory", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "tool_workspace",
    tool_names: "web_search"
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Retrieve tool guidelines before use
fetch("http://localhost:8002/retrieve_tool_memory", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    workspace_id: "tool_workspace",
    tool_names: "web_search"
  })
})
.then(response => response.json())
.then(data => console.log(data));
```
````