# 🚀 Vector Store API Guide

This guide covers the vector store implementations available in flowllm, their APIs, and how to use them effectively.

## 📋 Overview

flowllm provides multiple vector store backends for different use cases:

- **LocalVectorStore** (`backend=local`) - 📁 Simple file-based storage for development and small datasets
- **ChromaVectorStore** (`backend=chroma`) - 🔮 Embedded vector database for moderate scale
- **EsVectorStore** (`backend=elasticsearch`) - 🔍 Elasticsearch-based storage for production and large scale

All vector stores implement the `BaseVectorStore` interface, providing a consistent API across implementations.

## 🔄 Common API Methods

All vector store implementations share these core methods:

### Workspace Management

```python
# Check if workspace exists
store.exist_workspace(workspace_id: str) -> bool

# Create a new workspace
store.create_workspace(workspace_id: str, **kwargs)

# Delete a workspace
store.delete_workspace(workspace_id: str, **kwargs)

# Copy a workspace
store.copy_workspace(src_workspace_id: str, dest_workspace_id: str, **kwargs)
```

### Data Operations

```python
# Insert nodes (single or list)
store.insert(nodes: VectorNode | List[VectorNode], workspace_id: str, **kwargs)

# Delete nodes by ID
store.delete(node_ids: str | List[str], workspace_id: str, **kwargs)

# Search for similar nodes
store.search(query: str, workspace_id: str, top_k: int = 1, **kwargs) -> List[VectorNode]

# Iterate through workspace nodes
for node in store.iter_workspace_nodes(workspace_id: str, **kwargs):
    # Process each node
```

### Import/Export

```python
# Export workspace to file
store.dump_workspace(workspace_id: str, path: str | Path = "", callback_fn=None, **kwargs)

# Import workspace from file
store.load_workspace(workspace_id: str, path: str | Path = "", nodes: List[VectorNode] = None, 
                    callback_fn=None, **kwargs)
```

## ⚡ Vector Store Implementations

### 1. 📁 LocalVectorStore (`backend=local`)

A simple file-based vector store that saves data to local JSONL files.

#### 💡 When to Use
- **Development and testing** - No external dependencies required 🛠️
- **Small datasets** - Suitable for datasets with < 10,000 vectors 📊
- **Single-user applications** - Limited concurrent access support 👤

#### ⚙️ Configuration

```python
from flowllm.storage.vector_store import LocalVectorStore
from flowllm.embedding_model import OpenAICompatibleEmbeddingModel
from flowllm.utils.common_utils import load_env

# Load environment variables (for API keys)
load_env()

# Initialize embedding model
embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024, model_name="text-embedding-v4")

# Initialize vector store
vector_store = LocalVectorStore(
    embedding_model=embedding_model,
    store_dir="./file_vector_store",  # Directory to store JSONL files
    batch_size=1024                   # Batch size for operations
)
```

#### 💻 Example Usage

```python
from flowllm.schema.vector_node import VectorNode

# Create workspace
workspace_id = "my_workspace"
vector_store.create_workspace(workspace_id)

# Create nodes
nodes = [
    VectorNode(
        unique_id="node1",
        workspace_id=workspace_id,
        content="Artificial intelligence is revolutionizing technology",
        metadata={"category": "tech", "source": "article1"}
    ),
    VectorNode(
        unique_id="node2",
        workspace_id=workspace_id,
        content="Machine learning enables data-driven insights",
        metadata={"category": "tech", "source": "article2"}
    )
]

# Insert nodes
vector_store.insert(nodes, workspace_id)

# Search
results = vector_store.search("What is AI?", workspace_id, top_k=2)
for result in results:
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
    print(f"Score: {result.metadata.get('score', 'N/A')}")
```

### 2. 🔮 ChromaVectorStore (`backend=chroma`)

An embedded vector database that provides persistent storage with advanced features.

#### 💡 When to Use
- **Local development** with persistence requirements 🏠
- **Medium-scale applications** (10K - 1M vectors) 📈
- **Applications requiring metadata filtering** 🔍

#### ⚙️ Configuration

```python
from flowllm.storage.vector_store import ChromaVectorStore
from flowllm.embedding_model import OpenAICompatibleEmbeddingModel
from flowllm.utils.common_utils import load_env

# Load environment variables
load_env()

# Initialize embedding model
embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024, model_name="text-embedding-v4")

# Initialize vector store
vector_store = ChromaVectorStore(
    embedding_model=embedding_model,
    store_dir="./chroma_vector_store",  # Directory for Chroma database
    batch_size=1024                     # Batch size for operations
)
```

#### 💻 Example Usage

```python
from flowllm.schema.vector_node import VectorNode

workspace_id = "chroma_workspace"

# Check if workspace exists and create if needed
if not vector_store.exist_workspace(workspace_id):
    vector_store.create_workspace(workspace_id)

# Create nodes with metadata
nodes = [
    VectorNode(
        unique_id="node1",
        workspace_id=workspace_id,
        content="Deep learning models require large datasets",
        metadata={
            "category": "AI", 
            "difficulty": "advanced", 
            "topic": "deep_learning"
        }
    ),
    VectorNode(
        unique_id="node2",
        workspace_id=workspace_id,
        content="Transformer architecture revolutionized NLP",
        metadata={
            "category": "AI",
            "difficulty": "intermediate",
            "topic": "transformers"
        }
    )
]

# Insert nodes
vector_store.insert(nodes, workspace_id)

# Search
results = vector_store.search("deep learning", workspace_id, top_k=5)
for result in results:
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
```

### 3. 🔍 EsVectorStore (`backend=elasticsearch`)

Production-grade vector search using Elasticsearch with advanced filtering and scaling capabilities.

#### 💡 When to Use
- **Production environments** requiring high availability 🏭
- **Large-scale applications** (1M+ vectors) 🚀
- **Complex filtering requirements** on metadata 🎯

#### 🛠️ Setup Elasticsearch

Before using EsVectorStore, set up Elasticsearch:

##### Option 1: Docker Run
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

##### Environment Configuration
```bash
export FLOW_ES_HOSTS=http://localhost:9200
```

#### ⚙️ Configuration

```python
from flowllm.storage.vector_store import EsVectorStore
from flowllm.embedding_model import OpenAICompatibleEmbeddingModel
from flowllm.utils.common_utils import load_env
import os

# Load environment variables
load_env()

# Initialize embedding model
embedding_model = OpenAICompatibleEmbeddingModel(dimensions=1024, model_name="text-embedding-v4")

# Initialize vector store
vector_store = EsVectorStore(
    embedding_model=embedding_model,
    hosts=os.getenv("FLOW_ES_HOSTS", "http://localhost:9200"),  # Elasticsearch hosts
    basic_auth=None,                                           # ("username", "password") for auth
    batch_size=1024                                           # Batch size for bulk operations
)
```

#### 🎯 Advanced Filtering

EsVectorStore supports advanced filtering capabilities:

```python
# Add term filters
vector_store.add_term_filter("metadata.category", "technology")

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
from flowllm.schema.vector_node import VectorNode

# Define workspace
workspace_id = "production_workspace"

# Create workspace if needed
if not vector_store.exist_workspace(workspace_id):
    vector_store.create_workspace(workspace_id)

# Create nodes with rich metadata
nodes = [
    VectorNode(
        unique_id="doc1",
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
    print(f"Score: {result.metadata.get('score', 'N/A')}")
    print(f"Content: {result.content}")
    print(f"Metadata: {result.metadata}")
```

## 📝 Working with VectorNode

The `VectorNode` class is the fundamental data unit for all vector stores:

```python
from flowllm.schema.vector_node import VectorNode

# Create a node
node = VectorNode(
    unique_id="unique_identifier",     # Unique ID for the node (required)
    workspace_id="my_workspace",       # Workspace ID (required)
    content="Text content to embed",   # Content to be embedded (required)
    metadata={                         # Optional metadata
        "source": "document1",
        "category": "technology",
        "timestamp": "2024-08-29"
    },
    vector=None                        # Vector will be generated automatically if None
)
```

## 🔄 Import/Export Example

Export and import workspaces for backup or transfer:

```python
# Export workspace to file
vector_store.dump_workspace(
    workspace_id="my_workspace",
    path="./backup_data"  # Directory to store the exported data
)

# Import workspace from file
vector_store.load_workspace(
    workspace_id="new_workspace",
    path="./backup_data"  # Directory containing the exported data
)

# Copy workspace within the same store
vector_store.copy_workspace(
    src_workspace_id="original_workspace",
    dest_workspace_id="copied_workspace"
)
```

## 🧩 Integration with Embedding Models

All vector stores require an embedding model to function:

```python
from flowllm.embedding_model import OpenAICompatibleEmbeddingModel

# Initialize embedding model
embedding_model = OpenAICompatibleEmbeddingModel(
    dimensions=1024,             # Embedding dimensions
    model_name="text-embedding-v4",  # Model name
    batch_size=32                # Batch size for embedding generation
)

# Pass to vector store
vector_store = LocalVectorStore(
    embedding_model=embedding_model,
    store_dir="./vector_store"
)
```

🎉 This guide provides everything you need to work with vector stores in flowllm. Choose the implementation that best fits your use case and scale up as needed! ✨