# Configuration Guide

This document describes all available parameters for ExperienceMaker Service.
The application uses [OmegaConf](https://omegaconf.readthedocs.io/) for configuration management, supporting both YAML
files and command-line overrides.

## Basic Usage

```bash
experiencemaker [parameter1=value1] [parameter2=value2] ...
```

## Configuration Loading Priority

1. Default values from `AppConfig` dataclass
2. Pre-defined YAML configuration file (default: `demo_config.yaml`)
3. Custom YAML file (if `config_path` is specified)
4. Command-line overrides

## 🏗️ Configuration Architecture

ExperienceMaker uses a layered configuration system with the following priority order:

1. **Default Configuration** (lowest priority)
2. **YAML Configuration File**
3. **Command Line Arguments** (highest priority)

## 🧩 YAML Configuration Composition

The YAML configuration file follows a specific composition pattern that enables flexible and modular configuration:

### 1. Resource Declaration

First, you declare the three core resources that form the foundation of the system:

- **`llm`**: Language model configurations
- **`embedding_model`**: Embedding model configurations
- **`vector_store`**: Vector storage configurations

In these sections, `default` (or any custom name) represents a declared configuration object that can be referenced
later:

```yaml
llm:
  default: # This is a declared LLM configuration object
    backend: openai_compatible
    model_name: qwen3-32b

embedding_model:
  default: # This is a declared embedding model configuration object
    backend: openai_compatible
    model_name: text-embedding-v4

vector_store:
  default: # This is a declared vector store configuration object
    backend: local_file
    embedding_model: default
```

### 2. Operation Backend Registration

In the `op` section, each operation declares its `backend` implementation. The backend names are registered through
`@OP_REGISTRY.register()` decorator, typically converting camel-case class names to underscore format:

```yaml
op:
  recall_experience_op:
    backend: recall_experience_op    # Registered via @OP_REGISTRY.register()
```

### 3. Resource References

Operations reference the previously declared resources using their names:

```yaml
op:
  recall_experience_op:
    backend: recall_experience_op
    llm: default                     # References the declared LLM object
    embedding_model: default         # References the declared embedding model object
    vector_store: default            # References the declared vector store object
```

### 4. Pipeline Composition

Finally, using the declared operations, you can compose complex pipelines through nested structures and parallel
execution patterns:

```yaml
api:
  # Complex summarizer chain with parallel operations
  summarizer: trajectory_preprocess_op->[success_extraction_op|failure_extraction_op]->experience_validation_op

  # Nested retriever pipeline  
  retriever: recall_experience_op->rerank_experience_op->rewrite_experience_op
```

This compositional approach enables:

- **Modularity**: Declare resources once, reference everywhere
- **Flexibility**: Mix and match different backends and configurations
- **Complexity**: Build sophisticated processing chains through pipeline syntax

## 📁 Configuration Structure

```yaml
# Service Configuration
http_service:
  host: "0.0.0.0"
  port: 8001
  timeout_keep_alive: 600
  limit_concurrency: 64

# Pipeline Definitions  
api:
  retriever: recall_experience_op->rerank_experience_op->rewrite_experience_op
  summarizer: trajectory_preprocess_op->[success_extraction_op|failure_extraction_op]->experience_validation_op
  vector_store: vector_store_action_op

# Operation Configurations
op:
  operation_name:
    backend: operation_name   # Register through `@OP_REGISTRY.register()`, typically by converting camel-cased types into underscored names
    llm: default              # Optional: reference to LLM config, Register through `@LLM_REGISTRY.register()`
    embedding_model: default  # Optional: reference to embedding config, Register through `@EMBEDDING_MODEL_REGISTRY.register()`
    vector_store: default     # Optional: reference to vector store config, Register through `@VECTOR_STORE_REGISTRY.register()`
    params: # Operation-specific parameters
      param1: value1
      param2: value2

# Resource Configurations
llm:
  default:
    backend: openai_compatible
    model_name: qwen3-32b
    params:
      temperature: 0.6

embedding_model:
  default:
    backend: openai_compatible
    model_name: text-embedding-v4
    params:
      dimensions: 1024

vector_store:
  default:
    backend: local_file
    embedding_model: default
```

## 🔧 Pipeline Configuration

### Pipeline Syntax

Pipeline configurations use a special syntax to define operation flows:

- `->`: Sequential execution
- `[]`: Parallel execution group
- `|`: Alternative operations within parallel group

### Examples

```yaml
# Sequential pipeline
api:
  retriever: op1->op2->op3

  # Parallel execution
  summarizer: op1->[op2|op3|op4]->op5

  # Complex pipeline with nested parallel operations
  vector_store: preprocess_op->[recall_op->rerank_op|backup_op]->merge_op
```

## Basic Configuration Parameters

| Parameter            | Type   | Default Value   | Description                                                          | Example                                   |
|----------------------|--------|-----------------|----------------------------------------------------------------------|-------------------------------------------|
| `pre_defined_config` | string | `"demo_config"` | Name of the pre-defined configuration file (without .yaml extension) | `pre_defined_config=full_pipeline_config` |
| `config_path`        | string | `""`            | Path to custom configuration YAML file                               | `config_path=/path/to/config.yaml`        |

## HTTP Service Configuration

| Parameter                         | Type    | Default Value | Description                       | Example                               |
|-----------------------------------|---------|---------------|-----------------------------------|---------------------------------------|
| `http_service.host`               | string  | `"0.0.0.0"`   | Host address for the HTTP service | `http_service.host=127.0.0.1`         |
| `http_service.port`               | integer | `8001`        | Port number for the HTTP service  | `http_service.port=8080`              |
| `http_service.timeout_keep_alive` | integer | `600`         | Keep-alive timeout in seconds     | `http_service.timeout_keep_alive=600` |
| `http_service.limit_concurrency`  | integer | `64`          | Maximum concurrent connections    | `http_service.limit_concurrency=128`  |

## Thread Pool Configuration

| Parameter                 | Type    | Default Value | Description                      | Example                      |
|---------------------------|---------|---------------|----------------------------------|------------------------------|
| `thread_pool.max_workers` | integer | `10`          | Maximum number of worker threads | `thread_pool.max_workers=20` |

## API Pipeline Configuration

| Parameter          | Type   | Default Value | Description                              | Example                                                      |
|--------------------|--------|---------------|------------------------------------------|--------------------------------------------------------------|
| `api.retriever`    | string | `""`          | Pipeline definition for retriever API    | `api.retriever="build_query_op->recall_vector_store_op"`     |
| `api.summarizer`   | string | `""`          | Pipeline definition for summarizer API   | `api.summarizer="simple_summary_op->update_vector_store_op"` |
| `api.vector_store` | string | `""`          | Pipeline definition for vector store API | `api.vector_store="vector_store_action_op"`                  |

## Operation Configuration

Operations are configured using the pattern `op.{operation_name}.{parameter}`. Each operation can have the following
parameters:

| Parameter                    | Type   | Default Value | Description                                | Example                                                                                  |
|------------------------------|--------|---------------|--------------------------------------------|------------------------------------------------------------------------------------------|
| `op.{name}.backend`          | string | `""`          | Backend implementation class name          | `op.build_query_op.backend=build_query_op`                                               |
| `op.{name}.prompt_file_path` | string | `""`          | Path to prompt template file               | `op.react_op.prompt_file_path=/path/to/prompt.yaml`                                      |
| `op.{name}.prompt_dict`      | dict   | `{}`          | Direct prompt configuration dictionary     | `op.react_op.prompt_dict.system="You are an AI assistant"`                               |
| `op.{name}.llm`              | string | `""`          | Reference to LLM configuration             | `op.react_op.llm=default`                                                                |
| `op.{name}.embedding_model`  | string | `""`          | Reference to embedding model configuration | `op.recall_op.embedding_model=default`                                                   |
| `op.{name}.vector_store`     | string | `""`          | Reference to vector store configuration    | `op.recall_op.vector_store=default`                                                      |
| `op.{name}.params.{param}`   | any    | `{}`          | Operation-specific parameters              | The parameter reference is in [operations_documentation.md](operations_documentation.md) |

## LLM Configuration

| Parameter                   | Type   | Default Value | Description                | Example                                 |
|-----------------------------|--------|---------------|----------------------------|-----------------------------------------|
| `llm.{name}.backend`        | string | `""`          | LLM backend implementation | `llm.default.backend=openai_compatible` |
| `llm.{name}.model_name`     | string | `""`          | Model name identifier      | `llm.default.model_name=qwen3-32b`      |
| `llm.{name}.params.{param}` | any    | `{}`          | LLM-specific parameters    | `llm.default.params.temperature=0.6`    |

## Embedding Model Configuration

| Parameter                               | Type   | Default Value | Description                            | Example                                                |
|-----------------------------------------|--------|---------------|----------------------------------------|--------------------------------------------------------|
| `embedding_model.{name}.backend`        | string | `""`          | Embedding model backend implementation | `embedding_model.default.backend=openai_compatible`    |
| `embedding_model.{name}.model_name`     | string | `""`          | Embedding model name identifier        | `embedding_model.default.model_name=text-embedding-v4` |
| `embedding_model.{name}.params.{param}` | any    | `{}`          | Model-specific parameters              | `embedding_model.default.params.dimensions=1024`       |

## Vector Store Configuration

| Parameter                             | Type   | Default Value | Description                                | Example                                                   |
|---------------------------------------|--------|---------------|--------------------------------------------|-----------------------------------------------------------|
| `vector_store.{name}.backend`         | string | `""`          | Vector store backend implementation        | `vector_store.default.backend=elasticsearch`              |
| `vector_store.{name}.embedding_model` | string | `""`          | Reference to embedding model configuration | `vector_store.default.embedding_model=default`            |
| `vector_store.{name}.params.{param}`  | any    | `{}`          | Vector store-specific parameters           | `vector_store.default.params.store_dir=file_vector_store` |

## ⚙️ Custom Operation Parameters

### Operation Configuration Structure

```yaml
op:
  custom_operation:
    backend: custom_operation       # The backend names are registered through `@OP_REGISTRY.register()` decorator, typically converting camel-case class names to underscore format
    llm: default                    # Reference to LLM configuration
    vector_store: default           # Reference to vector store
    params: # Custom parameters for this operation
      retrieve_top_k: 15           # Number of top results to retrieve
      similarity_threshold: 0.8     # Similarity threshold for filtering
      enable_rerank: true          # Enable reranking functionality
      custom_param: "custom_value" # Any custom parameter
```

### Common Operation Parameters

**Retrieval Operations:**

```yaml
recall_experience_op:
  params:
    retrieve_top_k: 15
    similarity_threshold: 0.5

rerank_experience_op:
  params:
    enable_llm_rerank: true
    enable_score_filter: false
    top_k: 5
```

**Extraction Operations:**

```yaml
success_extraction_op:
  params:
    extraction_mode: "detailed"
    include_context: true

experience_validation_op:
  params:
    validation_threshold: 0.5
    strict_mode: false
```

## 🚀 Configuration Methods

### Method 1: Custom Configuration File

**Step 1:** Create your configuration file

```yaml
# my_custom_config.yaml
api:
  retriever: custom_recall_op->custom_rerank_op

op:
  custom_recall_op:
    backend: recall_experience_op
    params:
      retrieve_top_k: 20
      similarity_threshold: 0.7

llm:
  default:
    model_name: gpt-4
    params:
      temperature: 0.3
```

**Step 2:** Use the custom configuration

```bash
experiencemaker config_path=/path/to/my_custom_config.yaml
```

### Method 2: Command Line Parameters

Override any configuration parameter using dot notation:

```bash
# Basic parameter override
experiencemaker \
  llm.default.model_name=gpt-4 \
  embedding_model.default.model_name=text-embedding-3-large

# Operation parameters
experiencemaker \
  op.recall_experience_op.params.retrieve_top_k=20 \
  op.rerank_experience_op.params.top_k=8

# Service configuration
experiencemaker \
  http_service.port=8080 \
  thread_pool.max_workers=32

# Pipeline configuration  
experiencemaker \
  api.retriever="custom_op1->custom_op2"
```

### Method 3: Hybrid Approach

Combine configuration file with command line overrides:

```bash
experiencemaker \
  config_path=/path/to/base_config.yaml \
  llm.default.model_name=gpt-4 \
  op.recall_experience_op.params.retrieve_top_k=25
```

## 🎯 Practical Examples

### Example 1: High-Performance Configuration

```bash
experiencemaker \
  http_service.port=8002 \
  thread_pool.max_workers=64 \
  op.recall_experience_op.params.retrieve_top_k=50 \
  op.rerank_experience_op.params.top_k=10 \
  llm.default.params.temperature=0.1
```

### Example 2: Development Configuration

```yaml
# dev_config.yaml
http_service:
  port: 8003

api:
  retriever: recall_experience_op->rerank_experience_op

op:
  recall_experience_op:
    params:
      retrieve_top_k: 5  # Faster for development

  rerank_experience_op:
    params:
      top_k: 3

llm:
  default:
    model_name: qwen-turbo
    params:
      temperature: 0.8
```

```bash
experiencemaker config_path=dev_config.yaml
```

### Example 3: Multi-Backend Setup

```yaml
# multi_backend_config.yaml
llm:
  fast:
    backend: openai_compatible
    model_name: qwen-turbo
    params:
      temperature: 0.9

  accurate:
    backend: openai_compatible
    model_name: gpt-4
    params:
      temperature: 0.1

op:
  quick_extraction_op:
    backend: success_extraction_op
    llm: fast

  detailed_validation_op:
    backend: experience_validation_op
    llm: accurate
    params:
      validation_threshold: 0.8
```

## 📋 Configuration Tips

1. **Start Simple**: Begin with the default configuration and override specific parameters
2. **Use Environment Variables**: Set API keys and URLs in `.env` file
3. **Parameter Validation**: Invalid parameters will cause startup errors with detailed messages
4. **Performance Tuning**: Adjust `retrieve_top_k`, `top_k`, and `max_workers` based on your needs
5. **Pipeline Testing**: Use simple pipelines first, then gradually add complexity

## 🔍 Troubleshooting

### Common Issues

**Configuration Not Loading:**

```bash
# Check if config file exists and has correct YAML syntax
experiencemaker config_path=/full/path/to/config.yaml
```

**Parameter Override Not Working:**

```bash
# Use exact parameter path from configuration structure
experiencemaker op.operation_name.params.parameter_name=value
```

**Pipeline Syntax Errors:**

- Check for balanced brackets `[]`
- Ensure operation names exist in `op` section
- Use `|` only within `[]` groups

---

🎯 **Advanced Configuration Mastery!** You can now create sophisticated ExperienceMaker setups tailored to your specific
needs. 