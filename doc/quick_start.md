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
  llm.default.model_name=qwen3-32b \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=local_file
```
The service will start on `http://localhost:8001`

### Elasticsearch Backend
```bash
experiencemaker \
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

## 📝 Your First ExperienceMaker Script

### Call Summarizer Examples
```python
import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace"


def run_summary(messages: list):
    response = requests.post(url=base_url + "summarizer", json={
        "workspace_id": workspace_id,
        "traj_list": [
            {"messages": messages, "score": 1.0}
        ]
    })

    response = response.json()
    experience_list = response["experience_list"]
    for experience in experience_list:
        print(experience)
```

### Call Retriever Examples

```python
import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace"


def run_retriever(query: str):
    response = requests.post(url=base_url + "retriever", json={
        "workspace_id": workspace_id,
        "query": query,
    })

    response = response.json()
    experience_merged: str = response["experience_merged"]
    print(f"experience_merged={experience_merged}")
```

### Dump Experiences

```python
import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace1"


def dump_experience():
    response = requests.post(url=base_url + "vector_store", json={
        "workspace_id": workspace_id,
        "action": "dump",
        "path": "./",
    })
    print(response.json())
```

### Load Experiences

```python
import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace1"


def load_experience():
    response = requests.post(url=base_url + "vector_store", json={
        "workspace_id": "test_workspace2",
        "action": "load",
        "path": "./",
    })

    print(response.json())
```

Here, we have prepared a [simple react agent](../cookbook/simple_demo/simple_demo.py) to demonstrate how to enhance its
capabilities by integrating a summarizer and a retriever, thereby achieving better performance.

## 📚 Additional Resources

- **[Vector Store Setup](vector_store_setup.md)**: Production deployment guide
- **[Configuration Guide](configuration_guide.md)**: Advanced configuration options
- **[Operations Documentation](operations_documentation.md)**: Advanced operations configuration
- **[Example Collection](../cookbook)**: More practical examples

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