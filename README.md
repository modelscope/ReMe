# ExperienceMaker

<p align="center">
 <img src="doc/figure/logo.jpg" alt="ExperienceMaker Logo" width="100%">
</p>

<p align="center">
  <a href="https://pypi.org/project/experiencemaker/"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python Version"></a>
  <a href="https://pypi.org/project/experiencemaker/"><img src="https://img.shields.io/badge/pypi-v0.1.1-blue?logo=pypi" alt="PyPI Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="License"></a>
  <a href="https://github.com/modelscope/ExperienceMaker"><img src="https://img.shields.io/github/stars/modelscope/ExperienceMaker?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <strong>A comprehensive framework to make & reuse & share experience for AI agent</strong><br>
  <em>Empowering agents to learn from the past and excel in the future</em>
</p>

---

## 📰 What's New
- **[2025-08]** 🚀 MCP is now available! → [Quick Start Guide](./doc/mcp_quick_start.md)
- **[2025-07]** 🎉 ExperienceMaker v0.1.1 is now available on [PyPI](https://pypi.org/project/experiencemaker/)!
- **[2025-07]** 📚 Complete documentation and quick start guides released
- **[2025-06]** 🚀 Multi-backend vector store support (Elasticsearch & ChromaDB)

---

## 🚀 What's Next
- **Pre-built Experience Libraries**: Domain repositories (Finance/Coding/Education/Research) + community marketplace
- **Rich Experience Formats**: Executable code/tool configs/pipeline templates/workflows
- **Experience Validation**: Quality analysis + cross-task effectiveness + auto-refinement
- **Universal Trajectory Extraction**: Raw logs/multimodal data/execution traces → experiences

---

## 🌟 What is ExperienceMaker?
ExperienceMaker is a framework that transforms how AI agents learn and improve through **experience-driven intelligence**. 
By automatically extracting, storing, and intelligently reusing experiences from agent trajectories, it enables continuous learning and progressive skill enhancement.

### ✨ Core Capabilities

#### 🔍 **Intelligent Experience Summarizer**
- **Success Pattern Recognition**: Identify what works and understand the underlying principles
- **Failure Analysis**: Learn from mistakes to avoid repeating them in future tasks
- **Comparative Insights**: Understand the critical differences between successful and failed approaches
- **Multistep Trajectory Processing**: Break down complex tasks into learnable, actionable segments

#### 🎯 **Smart Experience Retriever**
- **Semantic Search**: Find relevant experiences using advanced embedding models and semantic understanding
- **Context-Aware Ranking**: Prioritize the most applicable experiences for current task contexts
- **Dynamic Rewriting**: Intelligently adapt experiences to fit new situations and requirements
- **Multi-modal Support**: Handle various input types including query, messages

#### 🗄️ **Scalable Experience Management**
- **Multiple Storage Backends**: Choose from Elasticsearch (production-ready), ChromaDB (development), or file-based storage (testing)
- **Workspace Isolation**: Organize experiences by projects, domains, or teams with complete separation
- **Deduplication & Validation**: Ensure high-quality, unique experience storage with automated quality control
- **Batch Operations**: Efficiently handle large-scale experience processing with optimized performance

#### 🔧 **Developer-Friendly Architecture**
- **REST API Interface**: Seamless integration with existing systems through clean API design
- **Modular Pipeline Design**: Compose custom workflows from atomic operations with maximum flexibility
- **Flexible Configuration**: YAML files and command-line overrides for easy customization
- **Experience Store**: Ready-to-use out of the box — there’s no need for you to manually summarize experiences. You can directly leverage existing, comprehensive experience datasets to greatly enhance your agent’s capabilities.
<p align="center">
 <img src="doc/figure/framework.png" alt="ExperienceMaker Architecture" width="70%">
</p>

---

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

Create a `.env` file in your project root directory:

```bash
# Required: LLM API configuration
LLM_API_KEY="sk-xxx"
LLM_BASE_URL="https://xxx.com/v1"

# Required: Embedding model configuration  
EMBEDDING_MODEL_API_KEY="sk-xxx"
EMBEDDING_MODEL_BASE_URL="https://xxx.com/v1"

# Optional: Elasticsearch configuration (if using Elasticsearch backend)

```

## 🚀 Quick Start

### 🌐 HTTP Service

For testing and development, use the `local_file` backend:
```bash
experiencemaker \
  http_service.port=8001 \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

💡 **Pro Tip**: Check out our [Configuration Guide](./doc/configuration_guide.md) for detailed configuration topics
including custom pipelines, operation parameters, and advanced configuration methods.

The service will start on `http://localhost:8001`

### 🔌 MCP Server

ExperienceMaker now supports Model Context Protocol (MCP) for seamless integration with MCP-compatible clients like Claude Desktop:

```bash
experiencemaker_mcp \
  mcp_transport=stdio \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

For SSE transport (Server-Sent Events):
```bash
experiencemaker_mcp \
  mcp_transport=sse \
  http_service.port=8001 \
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```

🔗 **For detailed MCP setup and usage examples**, see our [MCP Quick Start Guide](./doc/mcp_quick_start.md).

### 🔍 Production Setup with Elasticsearch Backend
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
📖 **Need Help?** Refer to [Vector Store Setup](./doc/vector_store_setup.md) for comprehensive deployment guidance.

## 📝 Your First ExperienceMaker Script

Here's how to get started!
Note the `workspace_id` serves as your experience storage namespace. Experiences in different workspaces remain completely isolated and cannot access each other.

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

💡 **Need More Advanced Operations?** For additional workspace management features(e.g. delete_workspace,
copy_workspace), advanced configuration options, and troubleshooting guidance, check out our
comprehensive [Quick Start Guide](./cookbook/simple_demo/quick_start.md).

🎭 **Want to See It in Action?** We've prepared a [simple react agent](./cookbook/simple_demo/simple_demo.py) that demonstrates how to enhance agent capabilities by integrating summarizer and retriever components, achieving significantly better performance.

---

## 🧪 Experiments

### 🌍 Experiment on Appworld

We test ExperienceMaker on Appworld with qwen3-8b:

| Method                         | pass@1    | pass@2      | pass@4    |
|--------------------------------|-----------|-------------|-----------|
| w/o ExperienceMaker (baseline) | 0.083     | 0.140       | 0.228     |
| **w ExperienceMaker**          |           |             |           |
|experience(Direct Use)     | **0.109** | 	**0.175**	 | **0.281** |

Pass@K measures the probability that at least one out of K generated samples successfully completes the task (achieves score=1).
The current experiments use an internal AppWorld environment which may have slight discrepancies, and we will soon update with experimental results from the standard AppWorld environment.

You may find more details to reproduce this experiment in [quickstart.md](cookbook/appworld/quickstart.md)


### 🧊 Experiment on Frozenlake

<table style="width: 40%; margin: 0 auto; border-collapse: collapse;">
  <thead>
    <tr>
      <th style="text-align: center; padding: 10px; border: 1px solid #ddd;">without experience</th>
      <th style="text-align: center; padding: 10px; border: 1px solid #ddd;">with experience</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center; padding: 10px; border: 1px solid #ddd;">
        <img src="doc/figure/frozenlake_failure.gif" alt="GIF 1" width="100%">
      </td>
      <td style="text-align: center; padding: 10px; border: 1px solid #ddd;">
        <img src="doc/figure/frozenlake_success.gif" alt="GIF 2" width="100%">
      </td>
    </tr>
  </tbody>
</table>

We test on 100 random frozenlake map with qwen3-8b:

| Method                        | pass rate        | 
|-------------------------------|------------------|
| w/o ExperienceMaker (baseline) | 0.66             | 
| **w ExperienceMaker**         |                  |
| [1] experience(Direct Use)    | 0.72 **(+9.1%)** |
| [2] experience(LLM Rewritten) | 0.72 **(+9.1%)** |

We also noticed that in such simple scenarios, not using LLM rewriting may actually yield better results. 

Therefore, in some simple scenarios, you can also try disabling LLM rewriting by simply changing the following in default_config.yaml:

```yaml
rewrite_experience_op:
  params:
    enable_llm_rewrite: false  # change this to false
```

You may find more details to reproduce this experiment in [quickstart.md](cookbook/frozenlake/quickstart.md)

### 🔧 Experiment on BFCL-V3

Coming Soon! Stay tuned for comprehensive evaluation results.

---

## 🏪 Ready-made Experience Store

ExperienceMaker provides pre-built experience libraries to jumpstart your agent's capabilities.
You can directly load these curated experiences into your workspace and start benefiting from accumulated knowledge
immediately.

### 📦 Available Experience Libraries

- **`appworld_v1.jsonl`**: Comprehensive experiences from Appworld agent interactions, covering complex task planning
  and execution patterns
- **`bfcl_v1.jsonl`**: Function calling experiences from Berkeley Function-Calling Leaderboard tasks

### 🚀 Quick Start with Pre-built Experiences

Here's how to load and use the Appworld experience library:

#### Step 1: Load Pre-built Experiences

<details open>
<summary><b>Python</b></summary>

```python
import requests

# Load Appworld experiences into your workspace
response = requests.post(url="http://0.0.0.0:8001/vector_store", json={
    "workspace_id": "appworld_v1",
    "action": "load",
    "path": "./library/",
})

print(f"loading result result={response.json()}")
```
</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/vector_store" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "appworld_v1",
    "action": "load",
    "path": "./library/"
  }'
```
</details>

#### Step 2: Retrieve Relevant Experiences

Now you can query the loaded experiences to get contextual guidance for your tasks:

<details open>
<summary><b>Python</b></summary>

```python
import requests

# Query for app interaction experiences
response = requests.post(url="http://0.0.0.0:8001/retriever", json={
    "workspace_id": "appworld_v1",
    "query": "How to navigate to settings and update user profile information?",
    "top_k": 1,
})

experience_merged = response.json()["experience_merged"]
print(f"Retrieved experiences: {experience_merged}")
```
</details>

<details>
<summary><b>curl</b></summary>

```bash
curl -X POST "http://0.0.0.0:8001/retriever" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "appworld_v1",
    "query": "How to navigate to settings and update user profile information?",
    "top_k": 1
  }'
```
</details>

---

## 📚 Additional Resources

- **[Quick Start](./cookbook/simple_demo/quick_start.md)**: This guide will help you get started with ExperienceMaker quickly using practical examples.
- **[Vector Store Setup](./doc/vector_store_setup.md)**: Complete production deployment guide
- **[Configuration Guide](./doc/configuration_guide.md)**: Describes all available command-line parameters for ExperienceMaker Service
- **[Operations Documentation](./doc/operations_documentation.md)**: Comprehensive operations configuration reference
- **[Example Collection](./cookbook)**: Practical examples and use cases
- **[Future RoadMap](./doc/future_roadmap.md)**: Our vision and upcoming features

---

## 🤝 Contributing
We warmly welcome contributions from the community! Here's how you can help make ExperienceMaker even better:

### 🐛 **Report Issues**
- Bug reports with detailed reproduction steps
- Feature requests and enhancement suggestions
- Documentation improvements and clarifications
- Performance optimization ideas

### 💻 **Code Contributions**
- New operations and tools development
- Backend implementations and optimizations
- API enhancements and new endpoints
- Test coverage improvements and quality assurance

### 📝 **Documentation**
- Usage examples and comprehensive tutorials
- Best practices guides and design patterns
- Translation and localization efforts

---
## 📄 Citation
If you use ExperienceMaker in your research or projects, please cite:
```bibtex
@software{ExperienceMaker,
  title = {ExperienceMaker: A Comprehensive Framework for AI Agent Experience Generation and Reuse},
  author = {The ExperienceMaker Team},
  url = {https://github.com/modelscope/ExperienceMaker},
  month = {08},
  year = {2025},
}
```

---
## ⚖️ License
This project is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.

---