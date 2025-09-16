---
title: Welcome to ReMe
summary: Memory Management Framework for Agents
order: 1
show_datetime: true
---

<p align="center">
 <img src="figure/reme_logo.png" alt="ReMe Logo" width="50%">
</p>

<div class="flex justify-center space-x-3">
  <a href="https://pypi.org/project/reme-ai/"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python Version"></a>
  <a href="https://pypi.org/project/reme-ai/"><img src="https://img.shields.io/badge/pypi-v0.1-blue?logo=pypi" alt="PyPI Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="License"></a>
  <a href="https://github.com/modelscope/ReMe"><img src="https://img.shields.io/github/stars/modelscope/ReMe?style=social" alt="GitHub Stars"></a>
</div>

<p align="center">
  <strong>ReMe (formerly MemoryScope): Memory Management Framework for Agents</strong><br>
  <em>Remember Me, Refine Me.</em>
</p>

---

ReMe provides AI agents with a unified memory system—enabling the ability to extract, reuse, and share memories across
users, tasks, and agents.

!!! info "Personal Memory + Task Memory = Agent Memory"

Personal memory helps "**understand user preferences**", while task memory helps agents "**perform better**".



## Architecture Design

<p align="center">
 <img src="figure/reme_structure.jpg" alt="ReMe Logo" width="100%">
</p>

ReMe integrates two complementary memory capabilities:

!!! note "Task Memory/Experience"

    ---

    Procedural knowledge reused across agents

    - **Success Pattern Recognition**: Identify effective strategies and understand their underlying principles
    - **Failure Analysis Learning**: Learn from mistakes and avoid repeating the same issues
    - **Comparative Patterns**: Different sampling trajectories provide more valuable memories through comparison
    - **Validation Patterns**: Confirm the effectiveness of extracted memories through validation modules

    Learn more about how to use task memory from [task memory](task_memory/task_memory.md)

!!! note "Personal Memory"

    Contextualized memory for specific users

    - **Individual Preferences**: User habits, preferences, and interaction styles
    - **Contextual Adaptation**: Intelligent memory management based on time and context
    - **Progressive Learning**: Gradually build deep understanding through long-term interaction
    - **Time Awareness**: Time sensitivity in both retrieval and integration

    Learn more about how to use personal memory from [personal memory](personal_memory/personal_memory.md)


## Installation

### Install from PyPI (Recommended)

```bash
pip install reme-ai
```

### Install from Source

```bash
git clone https://github.com/modelscope/ReMe.git
cd ReMe
pip install .
```

### Environment Configuration

Copy `example.env` to .env and modify the corresponding parameters:

```bash
FLOW_APP_NAME=ReMe
FLOW_LLM_API_KEY=sk-xxxx
FLOW_LLM_BASE_URL=https://xxxx/v1
FLOW_EMBEDDING_API_KEY=sk-xxxx
FLOW_EMBEDDING_BASE_URL=https://xxxx/v1
```

---

## Quick Start

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

```python
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

<details>
<summary>curl version</summary>

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

</details>

<details>
<summary>Node.js version</summary>

```javascript
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

</details>

#### Personal Memory Management

```python
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

<details>
<summary>curl version</summary>

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

</details>

<details>
<summary>Node.js version</summary>

```javascript
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

</details>

---

## Resources
- **[Personal memory](personal_memory/personal_memory.md)** & **[Task memory](task_memory/task_memory.md)** : Operators used in personal memory and task memory, You can modify the config to customize the pipelines.
- **[Example Collection](cookbook/experiment_overview.md)**: Real use cases and best practices
- **[Library](./library/library.md)**: Directly use existing task memory/experience for your tasks, and you can also contribute more task memory/experience to us.
- **[Contribution](contribution.md)**: welcome to your contributions!
- **[Vector Storage Setup](vector_store_api_guide.md)**: Configure local/vector databases and usage
- **[MCP Guide](mcp_quick_start.md)**: Create MCP services

---

## Citation

```bibtex
@software{ReMe2025,
  title = {ReMe: Memory Management Framework for Agents},
  author = {Li Yu, Jiaji Deng, Zouying Cao},
  url = {https://github.com/modelscope/ReMe},
  year = {2025}
}
```
