# ExperienceMaker Advanced Configuration Guide

This guide covers advanced configuration topics including custom pipelines, operation parameters, and configuration
methods.

## 🏗️ Configuration Architecture

ExperienceMaker uses a layered configuration system with the following priority order:

1. **Default Configuration** (lowest priority)
2. **YAML Configuration File**
3. **Command Line Arguments** (highest priority)

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
    backend: operation_backend
    llm: default              # Optional: reference to LLM config
    embedding_model: default  # Optional: reference to embedding config  
    vector_store: default     # Optional: reference to vector store config
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
api:
  summarizer: op1->[op2|op3|op4]->op5

# Complex pipeline with nested parallel operations
api:
  retriever: preprocess_op->[recall_op->rerank_op|backup_op]->merge_op
```

## ⚙️ Custom Operation Parameters

### Operation Configuration Structure

```yaml
op:
  custom_operation:
    backend: custom_backend_name
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