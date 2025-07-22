# 🚀 Vector Store Quick Start Guide
This comprehensive guide covers all available vector store implementations in ExperienceMaker, their differences, use cases, and setup instructions.

## 📋 Overview
ExperienceMaker supports multiple vector store backends for different use cases and deployment scenarios:
- **FileVectorStore** (`backend=local_file`) - 📁 Local file-based storage for development and small datasets
- **ChromaVectorStore** (`backend=chroma`) - 🔮 Embedded vector database for local development and moderate scale
- **EsVectorStore** (`backend=elasticsearch`) - 🔍 Elasticsearch-based storage for production and large scale

## ⚡ Vector Store Implementations
### 1. 📁 FileVectorStore (`backend=local_file`)
A simple file-based vector store that saves data to local JSONL files. Perfect for development, testing, and small datasets.

#### 💡 When to Use
- **Development and testing** - No external dependencies required 🛠️
- **Small datasets** - Suitable for datasets with < 10,000 vectors 📊
- **Single-user applications** - No concurrent access support 👤
- **Prototyping** - Quick setup without infrastructure ⚡

#### ✨ Features
- ✅ No external dependencies
- ✅ Simple file-based persistence
- ✅ Built-in cosine similarity search
- ❌ No concurrent access support
- ❌ Limited scalability
- ❌ No advanced filtering

#### ⚙️ Configuration Parameters
```python
from experiencemaker.vector_store import FileVectorStore
from experiencemaker.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel

embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024, model_name="text-embedding-v4")

vector_store = FileVectorStore(
    embedding_model=embedding_model,
    store_dir="./file_vector_store",  # Directory to store JSONL files
    batch_size=1024                   # Batch size for operations
)
```

#### 💻 Example Usage
```python
# Create workspace and insert data
workspace_id = "my_workspace"
vector_store.create_workspace(workspace_id)

nodes = [
    VectorNode(
        workspace_id=workspace_id,
        content="Artificial intelligence is revolutionizing technology",
        metadata={"category": "tech", "source": "article1"}
    ),
    VectorNode(
        workspace_id=workspace_id,
        content="Machine learning enables data-driven insights",
        metadata={"category": "tech", "source": "article2"}
    )
]

vector_store.insert(nodes, workspace_id)

# Search
results = vector_store.search("What is AI?", workspace_id, top_k=2)
```

### 2. 🔮 ChromaVectorStore (`backend=chroma`)

An embedded vector database that provides persistent storage with advanced features while remaining easy to deploy.

#### 💡 When to Use
- **Local development** with persistence requirements 🏠
- **Medium-scale applications** (10K - 1M vectors) 📈
- **Multi-user applications** with moderate concurrency 👥
- **Applications requiring metadata filtering** 🔍
- **Docker deployments** without external database dependencies 🐳

#### ✨ Features
- ✅ Persistent embedded database
- ✅ Advanced metadata filtering
- ✅ Built-in vector indexing (HNSW)
- ✅ HTTP API support
- ✅ Concurrent access support
- ✅ Collection management
- ❌ Limited horizontal scaling

#### ⚙️ Configuration Parameters
```python
from experiencemaker.vector_store import ChromaVectorStore
from experiencemaker.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel

embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024, model_name="text-embedding-v4")

vector_store = ChromaVectorStore(
    embedding_model=embedding_model,
    store_dir="./chroma_vector_store",  # Directory for Chroma database
    batch_size=1024                     # Batch size for operations
)
```

#### 💻 Example Usage
```python
workspace_id = "chroma_workspace"

# Check if workspace exists
if not vector_store.exist_workspace(workspace_id):
    vector_store.create_workspace(workspace_id)

# Insert with metadata
nodes = [
    VectorNode(
        workspace_id=workspace_id,
        content="Deep learning models require large datasets",
        metadata={"category": "AI", "difficulty": "advanced", "topic": "deep_learning"}
    )
]

vector_store.insert(nodes, workspace_id)

# Search with results
results = vector_store.search("deep learning", workspace_id, top_k=5)
for result in results:
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
```

### 3. 🔍 EsVectorStore (`backend=elasticsearch`)

Production-grade vector search using Elasticsearch with advanced filtering, scaling, and enterprise features.

#### 💡 When to Use
- **Production environments** requiring high availability 🏭
- **Large-scale applications** (1M+ vectors) 🚀
- **High-throughput scenarios** with many concurrent users ⚡
- **Complex filtering requirements** on metadata 🎯
- **Distributed deployments** across multiple nodes 🌐
- **Enterprise environments** with existing Elasticsearch infrastructure 🏢

#### ✨ Features
- ✅ Horizontal scaling
- ✅ High availability and fault tolerance
- ✅ Advanced filtering and aggregations
- ✅ Real-time indexing and search
- ✅ Cluster management
- ✅ Enterprise security features
- ✅ Monitoring and analytics
- ❌ Complex setup and maintenance
- ❌ Higher resource requirements

#### 🛠️ Setup Elasticsearch

Before using EsVectorStore, you need to set up Elasticsearch. Choose one of the following methods:

##### Option 1: All-in-One Script (Recommended for Development) 🎯
```bash
curl -fsSL https://elastic.co/start-local | sh
```

##### Option 2: Docker Run with HTTP Host 🐳
```bash
# Pull the latest Elasticsearch image
docker pull docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0

# Run Elasticsearch container
docker run -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "xpack.license.self_generated.type=trial" \
  -e "http.host=0.0.0.0" \
  docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
```

##### 🔧 Environment Configuration
Set the Elasticsearch hosts environment variable:
```bash
export ES_HOSTS=http://localhost:9200
```

#### ⚙️ Configuration Parameters
```python
from experiencemaker.vector_store import EsVectorStore
from experiencemaker.embedding_model.openai_compatible_embedding_model import OpenAICompatibleEmbeddingModel
import os

embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024, model_name="text-embedding-v4")

vector_store = EsVectorStore(
    embedding_model=embedding_model,
    hosts=os.getenv("ES_HOSTS", "http://localhost:9200"),  # Elasticsearch hosts
    basic_auth=None,                                       # ("username", "password") for auth
    batch_size=1024,                                      # Batch size for bulk operations
    retrieve_filters=[]                                   # Pre-configured filters
)
```

#### 🎯 Advanced Filtering
EsVectorStore supports advanced filtering capabilities:

```python
# Add term filters
vector_store.add_term_filter("metadata.category", "technology")
vector_store.add_term_filter("metadata.language", "en")

# Add range filters
vector_store.add_range_filter("metadata.score", gte=0.8)
vector_store.add_range_filter("metadata.timestamp", gte="2024-01-01", lte="2024-12-31")

# Search with filters applied
results = vector_store.search("machine learning", workspace_id, top_k=10)

# Clear filters for next search
vector_store.clear_filter()
```

#### 💻 Example Usage
```python
from experiencemaker.schema.vector_node import VectorNode

# Configure connection
workspace_id = "production_workspace"

# Create workspace with custom mapping
if not vector_store.exist_workspace(workspace_id):
    vector_store.create_workspace(workspace_id)

# Insert with rich metadata
nodes = [
    VectorNode(
        workspace_id=workspace_id,
        content="Transformer architecture revolutionized NLP",
        metadata={
            "category": "AI",
            "subcategory": "NLP",
            "author": "research_team",
            "timestamp": "2024-01-15",
            "confidence": 0.95,
            "tags": ["transformer", "nlp", "attention"]
        }
    )
]

# Insert with refresh for immediate availability
vector_store.insert(nodes, workspace_id, refresh=True)

# Advanced search with filters
vector_store.add_term_filter("metadata.category", "AI")
vector_store.add_range_filter("metadata.confidence", gte=0.9)

results = vector_store.search("transformer models", workspace_id, top_k=5)

for result in results:
    print(f"Score: {result.metadata.get('_score', 'N/A')}")
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
```

## 📊 Comparison Matrix

| Feature              | FileVectorStore | ChromaVectorStore | EsVectorStore       |
|----------------------|-----------------|-------------------|---------------------|
| **Setup Complexity** | ⭐ Very Easy     | ⭐⭐ Easy           | ⭐⭐⭐⭐ Complex        |
| **Scalability**      | < 10K vectors   | < 1M vectors      | 10M+ vectors        |
| **Concurrency**      | Single user     | Moderate          | High                |
| **Persistence**      | JSONL files     | SQLite/DuckDB     | Distributed         |
| **Filtering**        | Basic           | Advanced          | Enterprise          |
| **Performance**      | Good for small  | Good for medium   | Excellent for large |
| **Resource Usage**   | Minimal         | Low-Medium        | High                |
| **Maintenance**      | None            | Low               | High                |
| **Production Ready** | ❌               | ⚠️ Limited        | ✅ Yes               |

🎉 This guide provides everything you need to get started with vector stores in ExperienceMaker. Choose the implementation that best fits your use case and scale up as needed! ✨ 