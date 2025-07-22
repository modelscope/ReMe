# ExperienceMaker

<p align="center">
 <img src="doc/logo_v2.png" alt="ExperienceMaker Logo" width="50%">
</p>

<p align="center">
  <a href="https://pypi.org/project/experiencemaker/"><img src="https://img.shields.io/badge/python-3.12+-blue" alt="Python Version"></a>
  <a href="https://pypi.org/project/experiencemaker/"><img src="https://img.shields.io/badge/pypi-v0.1.0-blue?logo=pypi" alt="PyPI Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="License"></a>
  <a href="https://github.com/modelscope/ExperienceMaker"><img src="https://img.shields.io/github/stars/modelscope/ExperienceMaker?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <strong>A comprehensive framework for AI agent experience generation and reuse</strong><br>
  <em>Empowering agents to learn from the past and excel in the future</em>
</p>

---

## 📰 What's New
- **[2025-08]** 🎉 ExperienceMaker v0.1.0 is now available on [PyPI](https://pypi.org/project/experiencemaker/)!
- **[2025-07]** 📚 Complete documentation and quick start guides released
- **[2025-07]** 🚀 Multi-backend vector store support (Elasticsearch & ChromaDB)

---

## 🌟 What is ExperienceMaker?
ExperienceMaker is a framework that revolutionizes how AI agents learn and improve through **experience-driven intelligence**. 
By automatically extracting, storing, and reusing experiences from agent trajectories, it enables continuous learning and progressive skill enhancement.

### 🚀 Why ExperienceMaker?
Traditional AI agents start from scratch with every new task, wasting valuable learning opportunities. 
ExperienceMaker changes this by:
- **🧠 Learning from History**: Automatically extract actionable insights from successful and failed attempts
- **🔄 Intelligent Reuse**: Apply relevant past experiences to solve new, similar problems
- **📈 Continuous Improvement**: Build a growing knowledge base that makes agents smarter over time
- **⚡ Faster Problem Solving**: Reduce trial-and-error by leveraging proven strategies

### ✨ Core Capabilities

#### 🔍 **Intelligent Experience Summarizer**
- **Success Pattern Recognition**: Identify what works and why
- **Failure Analysis**: Learn from mistakes to avoid repetition
- **Comparative Insights**: Understand the difference between successful and failed approaches
- **Multi-step Trajectory Processing**: Break down complex tasks into learnable segments

#### 🎯 **Smart Experience Retriever**
- **Semantic Search**: Find relevant experiences using advanced embedding models
- **Context-Aware Ranking**: Prioritize the most applicable experiences for current tasks
- **Dynamic Rewriting**: Adapt past experiences to fit new contexts
- **Multi-modal Support**: Handle various input types (queries, conversations, trajectories)

#### 🗄️ **Scalable Experience Management**
- **Multiple Storage Backends**: Choose from Elasticsearch (production), ChromaDB (development), or file-based (testing)
- **Workspace Isolation**: Organize experiences by projects, domains, or teams
- **Deduplication & Validation**: Ensure high-quality, unique experience storage
- **Batch Operations**: Efficiently handle large-scale experience processing

#### 🔧 **Developer-Friendly Architecture**
- **REST API Interface**: Easy integration with existing systems
- **Modular Pipeline Design**: Compose custom workflows from atomic operations
- **Flexible Configuration**: YAML files and command-line overrides
- **Comprehensive Monitoring**: Built-in logging and performance metrics

### 🏗️ Framework Architecture
<p align="center">
 <img src="doc/framework.png" alt="ExperienceMaker Architecture" width="70%">
</p>

ExperienceMaker follows a modular, scalable architecture designed for production use:
#### 🌐 **API Layer**
- **🔍 Retriever API**: Query-based and conversation-based experience retrieval
- **📊 Summarizer API**: Trajectory-to-experience conversion and storage  
- **🗄️ Vector Store API**: Database management and workspace operations
- **🤖 Agent API**: ReAct-based agent execution with experience enhancement
#### ⚙️ **Processing Pipeline**
Our atomic operations can be composed into powerful pipelines:
**Retrieval Pipeline**:
```
build_query_op->recall_vector_store_op->merge_experience_op
```
**Summarization Pipeline**:
```
simple_summary_op->update_vector_store_op
```

#### 🔌 **Extensible Components**
- **LLM Integration**: OpenAI-compatible APIs with flexible model switching
- **Embedding Models**: Pluggable embedding providers for semantic search
- **Vector Stores**: Multiple backends for different deployment scenarios
- **Tools & Operators**: Extensible library of processing operations

---

## 🛠️ Installation

### Prerequisites
- Python 3.12+
- LLM API access (openAI compatible models)
- Embedding model API access

### Quick Install

```bash
# Install from PyPI (recommended)
pip install experiencemaker

# Or install from source
git clone https://github.com/modelscope/ExperienceMaker.git
cd ExperienceMaker
pip install .
```

---

## ⚡ Quick Start

### 1. Environment Setup

Configure your API credentials:

```bash
# LLM Configuration
export LLM_API_KEY="your-api-key-here"
export LLM_BASE_URL="https://xxxx.com/v1"

# Embedding Model Configuration  
export EMBEDDING_MODEL_API_KEY="your-api-key-here"
export EMBEDDING_MODEL_BASE_URL="https://xxxx.com/v1"

# Optional: Elasticsearch
export ES_HOSTS="http://localhost:9200"
```

### 2. Launch ExperienceMaker Service

Start with a single command:

```bash
experiencemaker \
  llm.default.model_name=gpt-4o \
  embedding_model.default.model_name=text-embedding-3-small \
  vector_store.default.backend=local_file
```
> 📚 **Need Help?** Check our [Services Params Documentation](./doc/service_params.md) for detailed instructions.


### 3. Vector Store Setup(Optional)
if you want to use Elasticsearch as your vector store, you can follow these steps:

```bash
vector_store.default.backend=elasticsearch
```

```bash
# Quick setup (recommended)
curl -fsSL https://elastic.co/start-local | sh

# Verify connection
curl http://localhost:9200/_cluster/health
```

> 📚 **Need Help?** Check our [Vector Store Setup Guide](./doc/vector_store_quick_start.md) for detailed instructions.

---

## 🎯 Usage Examples

### Call Summarizer Examples

```python
import json

import requests
from dotenv import load_dotenv

load_dotenv()
base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace"


def run_summary(messages: list, dump_experience: bool = True):
    response = requests.post(url=base_url + "summarizer", json={
        "workspace_id": workspace_id,
        "traj_list": [
            {"messages": messages, "score": 1.0}
        ]
    })

    response = response.json()
    experience_list = response["experience_list"]
    if dump_experience:
        with open("experience.jsonl", "w") as f:
            f.write(json.dumps(experience_list, indent=2, ensure_ascii=False))
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
    return experience_merged
```

### Vector Store Management

```python
def manage_vector_store(action: str, workspace_id: str, **params):
    """Comprehensive vector store management"""
    response = requests.post(
        f"{BASE_URL}/vector_store",
        json={
            "workspace_id": workspace_id,
            "action": action,
            **params
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Action '{action}' failed: {response.text}")
        return None

# Example operations
workspace = "production_workspace"

# Create workspace
manage_vector_store("create", workspace)

# Check workspace stats
stats = manage_vector_store("stats", workspace)
if stats:
    print(f"Workspace '{workspace}': {stats['total_experiences']} experiences")

# Backup experiences
manage_vector_store("dump", workspace, path="./backup/experiences.jsonl")

# Restore from backup
manage_vector_store("load", workspace, path="./backup/experiences.jsonl")

# Clean up workspace
manage_vector_store("clear", workspace)
```


### Advanced: Custom Pipeline Configuration

```python
# Create custom configuration file
config = """
http_service:
  host: "0.0.0.0"
  port: 8001

# Custom retrieval pipeline
api:
  retriever: "build_query_op->recall_experience_op->rerank_experience_op->rewrite_experience_op"
  summarizer: "trajectory_preprocess_op->success_extraction_op->experience_validation_op->experience_storage_op"

# LLM Configuration
llm:
  default:
    backend: openai_compatible
    model_name: gpt-4o
    params:
      temperature: 0.7
      max_tokens: 4000

# Embedding Configuration
embedding_model:
  default:
    backend: openai_compatible
    model_name: text-embedding-3-small

# Vector Store Configuration
vector_store:
  default:
    backend: elasticsearch
    embedding_model: default

# Operation-specific parameters
op:
  recall_experience_op:
    params:
      retrieve_top_k: 10
      query_enhancement: true
  
  rerank_experience_op:
    params:
      enable_llm_rerank: true
      top_k: 5
      min_score_threshold: 0.3
  
  experience_validation_op:
    params:
      validation_threshold: 0.4
"""

# Save and use custom configuration
with open("custom_config.yaml", "w") as f:
    f.write(config)

# Launch with custom configuration
# experiencemaker config_path=custom_config.yaml
```



---

## 🔧 Configuration

ExperienceMaker offers flexible configuration through YAML files and command-line parameters:

### Configuration Methods

1. **Default Configuration**: Built-in sensible defaults
2. **YAML Configuration**: Structured configuration files
3. **Environment Variables**: Runtime configuration
4. **Command-line Overrides**: Dynamic parameter adjustment

### Key Configuration Areas

| Category | Description | Example |
|----------|-------------|---------|
| **HTTP Service** | Server host, port, timeouts | `http_service.port=8080` |
| **LLM Models** | Model names, parameters, endpoints | `llm.default.model_name=gpt-4o` |
| **Embedding Models** | Embedding services and dimensions | `embedding_model.default.model_name=text-embedding-3-small` |
| **Vector Stores** | Backend type, connection settings | `vector_store.default.backend=elasticsearch` |
| **Operations** | Pipeline configurations, thresholds | `op.rerank_experience_op.params.top_k=5` |

### Example Configuration Commands

```bash
# Basic setup
experiencemaker llm.default.model_name=gpt-4o vector_store.default.backend=chroma

# Advanced configuration
experiencemaker \
  config_path=my_config.yaml \
  http_service.port=8002 \
  op.recall_experience_op.params.retrieve_top_k=15 \
  op.rerank_experience_op.params.enable_llm_rerank=true \
  vector_store.default.backend=elasticsearch
```

> 📖 **Complete Reference**: See our [Configuration Guide](./doc/global_params.md) for all available parameters.

---

## 🏢 Production Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install .

EXPOSE 8001

CMD ["experiencemaker", "http_service.host=0.0.0.0", "vector_store.default.backend=elasticsearch"]
```

### Kubernetes Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: experiencemaker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: experiencemaker
  template:
    metadata:
      labels:
        app: experiencemaker
    spec:
      containers:
      - name: experiencemaker
        image: experiencemaker:latest
        ports:
        - containerPort: 8001
        env:
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: llm-api-key
        - name: ES_HOSTS
          value: "http://elasticsearch:9200"
        command: ["experiencemaker"]
        args: 
        - "vector_store.default.backend=elasticsearch"
        - "http_service.host=0.0.0.0"
```

### Performance Considerations

- **Elasticsearch**: Recommended for >100K experiences
- **ChromaDB**: Suitable for <1M experiences  
- **Load Balancing**: Multiple service instances for high availability
- **Caching**: Redis for frequently accessed experiences
- **Monitoring**: Integrate with Prometheus/Grafana

---

## 📚 Documentation & Resources

### 📖 **Core Documentation**
- [📋 Operations Reference](./doc/operations.md) - Complete list of all available operations
- [⚙️ Configuration Guide](./doc/global_params.md) - Detailed parameter documentation  
- [🗄️ Vector Store Setup](./doc/vector_store_quick_start.md) - Backend setup instructions
- [🧪 Quick Start Examples](./cookbook/simple_demo/) - Working code samples

### 🎓 **Learning Resources**
- [📘 Cookbook Examples](./cookbook/) - Real-world use cases and patterns
- [🚀 Best Practices](./cookbook/) - Production deployment guidelines
- [🔧 Troubleshooting](./cookbook/) - Common issues and solutions

### 🔗 **API Reference**
- **Retriever API**: Experience search and retrieval
- **Summarizer API**: Trajectory processing and storage
- **Vector Store API**: Database management operations
- **Agent API**: ReAct-based agent execution

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### 🐛 **Report Issues**
- Bug reports and feature requests
- Documentation improvements
- Performance optimization suggestions

### 💻 **Code Contributions**
- New operations and tools
- Backend implementations
- API enhancements
- Test coverage improvements

### 📝 **Documentation**
- Usage examples and tutorials
- Best practices and patterns
- Translation and localization

**Getting Started**: Fork the repository, create a feature branch, and submit a pull request. Please follow our coding standards and include tests for new functionality.

---

## 🎯 Use Cases & Success Stories

### 🤖 **AI Agent Development**
- **Code Generation Agents**: Learn successful coding patterns and avoid common bugs
- **Research Assistants**: Build domain expertise through accumulated research experiences  
- **Customer Support**: Improve response quality using past successful interactions

### 🏢 **Enterprise Applications**
- **Knowledge Management**: Capture and reuse organizational expertise
- **Process Automation**: Learn optimal workflows from successful completions
- **Decision Support**: Leverage historical decision outcomes for better choices

### 📊 **Data Science & Analytics**
- **Model Development**: Learn from past experimentation results
- **Feature Engineering**: Reuse successful feature combinations
- **Pipeline Optimization**: Apply proven processing strategies

---

## 📄 Citation

If you use ExperienceMaker in your research or projects, please cite:

```bibtex
@software{ExperienceMaker,
  title = {ExperienceMaker: A Comprehensive Framework for AI Agent Experience Generation and Reuse},
  author = {The ExperienceMaker Team},
  url = {https://github.com/modelscope/ExperienceMaker},
  month = {January},
  year = {2025},
  note = {Version 0.1.0}
}
```

---

## ⚖️ License

This project is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

ExperienceMaker is built with ❤️ by the team at ModelScope. Special thanks to:

- The open-source community for valuable feedback and contributions
- Research teams advancing the field of AI agent learning
- Early adopters providing real-world usage insights

---

<p align="center">
  <strong>Ready to supercharge your AI agents with experience? 🚀</strong><br>
  <a href="#-installation">Get Started Now</a> · 
  <a href="./doc/">Read the Docs</a> · 
  <a href="https://github.com/modelscope/ExperienceMaker">Star on GitHub</a>
</p>

<p align="center">
  Made with ❤️ by the <strong>ExperienceMaker Team</strong>
</p>
