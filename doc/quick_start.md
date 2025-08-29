# ExperienceMaker Quick Start Guide
This guide will help you get started with ExperienceMaker quickly using practical examples.

## 🚀 What You'll Learn
- How to set up ExperienceMaker service
- Run an agent and generate experiences
- Retrieve and apply experiences to new tasks
- Build experience-enhanced agents

## 📋 Prerequisites
- Python 3.12+
- LLM API access (OpenAI or compatible)
- Embedding model API access

## 🛠️ Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install experiencemaker
```

### Option 2: Install from Source

```bash
git clone https://github.com/modelscope/ExperienceMaker.git
cd ExperienceMaker
pip install .
```

## ⚙️ Environment Setup
Create a `.env` file in your project directory:

```bash
# Required: LLM API configuration
LLM_API_KEY="sk-xxx"
LLM_BASE_URL="https://xxx.com/v1"

# Required: Embedding model configuration  
EMBEDDING_MODEL_API_KEY="sk-xxx"
EMBEDDING_MODEL_BASE_URL="https://xxx.com/v1"

# Optional: Elasticsearch configuration (if using Elasticsearch backend)

```

## 🚀 Start the Service
For testing, use the `local_file` backend:
```bash
experiencemaker \
  http_service.port=8001 \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```
The service will start on `http://localhost:8001`

### Elasticsearch Backend
```bash
experiencemaker \
  http_service.port=8001 \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=elasticsearch
```

**Setup Elasticsearch:**
```bash
export ES_HOSTS="http://localhost:9200"
# Quick setup using Elastic's official script
curl -fsSL https://elastic.co/start-local | sh
```

📖 **Need Help?** Refer to [Vector Store Setup](../../doc/vector_store_setup.md) for comprehensive deployment guidance.

## 📝 Your First ExperienceMaker Script

Here's how to get started!
Note the `workspace_id` serves as your experience storage namespace. Experiences in different workspaces remain
completely isolated and cannot access each other.

### 📊 Call Summarizer Examples

Transform conversation trajectories into valuable experiences using batch summarization. Each trajectory contains:

- **Message**: Complete conversation history between user and agent
- **Score**: Performance rating (0-1 scale, where 0=failure, 1=success)

The summarizer analyzes these trajectories to extract actionable insights and patterns for future interactions.

<details open>
<summary><b>Python</b></summary>

```python
import requests

response = requests.post(url="http://0.0.0.0:8001/summarizer", json={
  "workspace_id": "test_workspace",
  "traj_list": [
    {"messages": [{"role": "user", "content": "hello world"}], "score": 1.0}
  ]
})

experience_list = response.json()["experience_list"]
for experience in experience_list:
  print(experience)
```

</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/summarizer" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "traj_list": [
      {
        "messages": [{"role": "user", "content": "hello world"}],
        "score": 1.0
      }
    ]
  }'
```

</details>

<details>
<summary><b>Node.js</b></summary>

```javascript
const fetch = require('node-fetch');
// or: import fetch from 'node-fetch';

async function callSummarizer() {
  try {
    const response = await fetch('http://0.0.0.0:8001/summarizer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workspace_id: "test_workspace",
        traj_list: [
          {
            messages: [{ role: "user", content: "hello world" }],
            score: 1.0
          }
        ]
      })
    });

    const data = await response.json();
    const experienceList = data.experience_list;
    
    experienceList.forEach(experience => {
      console.log(experience);
    });
  } catch (error) {
    console.error('Error:', error);
  }
}

callSummarizer();
```

</details>

### 🔍 Call Retriever Examples

Intelligently search and retrieve the most relevant experiences from your workspace to enhance decision-making. The retriever:

- **Finds** the top-k most similar experiences based on semantic similarity to your query
- **Returns** pre-assembled context ready for immediate use, or raw experience data for custom processing
- **Leverages** your workspace's accumulated knowledge to provide contextually relevant insights

<details open>
<summary><b>Python</b></summary>

```python
import requests

response = requests.post(url="http://0.0.0.0:8001/retriever", json={
  "workspace_id": "test_workspace",
  "query": "what is the meaning of life?",
  "top_k": 1,
})

experience_merged: str = response.json()["experience_merged"]
print(f"experience_merged={experience_merged}")
```

</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/retriever" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "query": "what is the meaning of life?",
    "top_k": 1
  }'
```

</details>

<details>
<summary><b>Node.js</b></summary>

```javascript
const fetch = require('node-fetch');
// or: import fetch from 'node-fetch';

async function callRetriever() {
  try {
    const response = await fetch('http://0.0.0.0:8001/retriever', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workspace_id: "test_workspace",
        query: "what is the meaning of life?",
        top_k: 1
      })
    });

    const data = await response.json();
    const experienceMerged = data.experience_merged;
    
    console.log(`experience_merged=${experienceMerged}`);
  } catch (error) {
    console.error('Error:', error);
  }
}

callRetriever();
```

</details>

### 💾 Dump Experiences From Vector Store

Export and backup your valuable experience data for archival, analysis, or migration purposes. This operation:

- **Extracts** all experiences from the specified workspace in the vector store
- **Saves** them to a structured JSONL file at `{path}/{workspace_id}.jsonl`
- **Preserves** complete experience metadata and embeddings for future restoration

<details open>
<summary><b>Python</b></summary>

```python
import requests

response = requests.post(url="http://0.0.0.0:8001/vector_store", json={
  "workspace_id": "test_workspace",
  "action": "dump",
  "path": "./",
})
print(response.json())
```

</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "action": "dump",
    "path": "./"
  }'
```

</details>

<details>
<summary><b>Node.js</b></summary>

```javascript
const fetch = require('node-fetch');
// or: import fetch from 'node-fetch';

async function dumpExperiences() {
  try {
    const response = await fetch('http://0.0.0.0:8001/vector_store', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workspace_id: "test_workspace",
        action: "dump",
        path: "./"
      })
    });

    const data = await response.json();
    console.log(data);
  } catch (error) {
    console.error('Error:', error);
  }
}

dumpExperiences();
```

</details>

### 📥 Load Experiences To Vector Store

Import and restore previously exported experience data to populate your workspace with existing knowledge. This operation:

- **Reads** experience data from the JSONL file located at `{path}/{workspace_id}.jsonl`
- **Reconstructs** the vector embeddings and indexes them in the specified workspace
- **Enables** immediate access to imported experiences for retrieval and decision-making

<details open>
<summary><b>Python</b></summary>

```python
import requests

response = requests.post(url="http://0.0.0.0:8001/vector_store", json={
  "workspace_id": "test_workspace",
  "action": "load",
  "path": "./",
})

print(response.json())
```

</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "action": "load",
    "path": "./"
  }'
```

</details>

<details>
<summary><b>Node.js</b></summary>

```javascript
const fetch = require('node-fetch');
// or: import fetch from 'node-fetch';

async function loadExperiences() {
  try {
    const response = await fetch('http://0.0.0.0:8001/vector_store', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workspace_id: "test_workspace",
        action: "load",
        path: "./"
      })
    });

    const data = await response.json();
    console.log(data);
  } catch (error) {
    console.error('Error:', error);
  }
}

loadExperiences();
```

</details>


### 🗑️ Delete Workspace

Permanently remove a workspace and all its associated experience data when it's no longer needed. This operation:

- **Removes** all experiences, embeddings, and metadata from the specified workspace
- **Frees up** storage space and computational resources
- **Cannot be undone** - ensure you've backed up important data before deletion

<details open>
<summary><b>Python</b></summary>

```python
import requests

response = requests.post(url="http://0.0.0.0:8001/vector_store", json={
    "workspace_id": "test_workspace",
    "action": "delete"
})

print(response.json())
```

</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "action": "delete"
  }'
```

</details>

<details>
<summary><b>Node.js</b></summary>

```javascript
const fetch = require('node-fetch');
// or: import fetch from 'node-fetch';

async function deleteWorkspace() {
  try {
    const response = await fetch('http://0.0.0.0:8001/vector_store', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workspace_id: "test_workspace",
        action: "delete"
      })
    });

    const data = await response.json();
    console.log(data);
  } catch (error) {
    console.error('Error:', error);
  }
}

deleteWorkspace();
```

</details>

### 📋 Copy Workspace

Duplicate an existing workspace to create a new one with identical experience data, perfect for experimentation or branching. This operation:

- **Clones** all experiences and embeddings from the source workspace
- **Creates** a new independent workspace with the copied data
- **Preserves** original workspace while enabling safe testing and modifications in the copy

<details open>
<summary><b>Python</b></summary>

```python
import requests

response = requests.post(url="http://0.0.0.0:8001/vector_store", json={
    "workspace_id": "test_workspace",
    "action": "copy",
    "src_workspace_id": "src_workspace"
})

print(response.json())
```

</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "test_workspace",
    "action": "copy",
    "src_workspace_id": "src_workspace"
  }'
```

</details>

<details>
<summary><b>Node.js</b></summary>

```javascript
const fetch = require('node-fetch');
// or: import fetch from 'node-fetch';

async function copyWorkspace() {
  try {
    const response = await fetch('http://0.0.0.0:8001/vector_store', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        workspace_id: "test_workspace",
        action: "copy",
        src_workspace_id: "src_workspace"
      })
    });

    const data = await response.json();
    console.log(data);
  } catch (error) {
    console.error('Error:', error);
  }
}

copyWorkspace();
```

</details>

🎭 **Want to See It in Action?** We've prepared a [simple react agent](../../cookbook/simple_demo/simple_demo.py) that
demonstrates how to enhance agent capabilities by integrating summarizer and retriever components, achieving
significantly better performance.

## 🐛 Common Issues

### Service Won't Start
- Check if port 8001 is available
- Verify your API keys in `.env` file
- Ensure Python version is 3.12+

### No Experiences Retrieved
- Make sure you've run the summarizer first
- Check if workspace_id matches between operations
- Verify vector store backend is properly configured

### API Connection Errors
- Confirm LLM_BASE_URL and API keys are correct
- Test API access independently
- Check network connectivity

---

🎯 **You're all set!** You now have a working ExperienceMaker setup that can learn from interactions and improve over time. 