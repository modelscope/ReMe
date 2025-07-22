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

## 🎯 Step-by-Step Walkthrough

### Step 1: Run Your First Agent

```bash
python demo.py
```

This will:
1. Send a query to the agent
2. Get an analysis of Tesla's business model
3. Save the conversation messages

### Step 2: Understand the Experience Generation

The agent's conversation will be processed to extract:
- **Success patterns**: What worked well in the analysis
- **Key insights**: Important findings and methodologies
- **Failure cases**: What didn't work or could be improved

### Step 3: Experience Retrieval in Action

When you ask about Apple, the system will:
1. Search for relevant experiences (Tesla analysis)
2. Find similar business analysis patterns
3. Apply learned methodologies to the new query

## 🔧 Advanced Usage

### Custom Workspace Management

```python
def manage_workspace(action: str):
    """Manage vector store workspace"""
    response = requests.post(
        url=f"{base_url}/vector_store",
        json={
            "workspace_id": workspace_id,
            "action": action
        }
    )
    return response.json()

# Create a new workspace
manage_workspace("create")

# Clear all experiences
manage_workspace("clear")

# Dump experiences to file
requests.post(
    url=f"{base_url}/vector_store",
    json={
        "workspace_id": workspace_id,
        "action": "dump",
        "path": "./backup/experiences.jsonl"
    }
)
```

### Batch Experience Processing

```python
def batch_process_experiences(queries: list):
    """Process multiple queries and build experience base"""
    all_experiences = []
    
    for i, query in enumerate(queries):
        print(f"Processing query {i+1}/{len(queries)}: {query}")
        
        # Run agent
        messages = run_agent(query)
        
        # Generate experiences
        run_summary(messages, dump_experience=False)
        
    print(f"Processed {len(queries)} queries and built experience base")

# Example: Build experience base for financial analysis
financial_queries = [
    "Analyze Tesla's revenue streams",
    "Evaluate Apple's market position", 
    "Assess Microsoft's competitive advantages"
]

batch_process_experiences(financial_queries)
```

## 🔍 Monitoring and Debugging

### Check Service Status

```python
def check_service_health():
    """Check if ExperienceMaker service is running"""
    try:
        response = requests.get(f"{base_url}/health")
        return response.status_code == 200
    except:
        return False

if not check_service_health():
    print("❌ ExperienceMaker service is not running")
    print("Start it with: experiencemaker vector_store.default.backend=local_file")
else:
    print("✅ ExperienceMaker service is running")
```

### View Generated Files

After running the demo, you'll have:

- `messages.jsonl`: Raw conversation data
- `experience.jsonl`: Structured experiences extracted from conversations

## 🎉 What's Next?

Now that you have ExperienceMaker running:

1. **Explore Different Domains**: Try queries in different areas (technical analysis, creative writing, problem-solving)

2. **Build Domain-Specific Experience**: Create workspaces for specific use cases

3. **Integration**: Integrate ExperienceMaker into your existing agent workflows

4. **Production Deployment**: Switch to Elasticsearch for production workloads

## 📚 Additional Resources

- **[Full Documentation](./README.md)**: Complete feature reference
- **[Vector Store Setup](./doc/vector_store_quick_start.md)**: Production deployment guide  
- **[Configuration Guide](./doc/global_params.md)**: Advanced configuration options
- **[Example Collection](./cookbook/)**: More practical examples

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