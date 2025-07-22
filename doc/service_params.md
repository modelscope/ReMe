# Services Params Documentation

This document describes all available command-line parameters for ExperienceMaker. The application
uses [OmegaConf](https://omegaconf.readthedocs.io/) for configuration management, supporting both YAML files and
command-line overrides.

## Basic Usage

```bash
experiencemaker [parameter1=value1] [parameter2=value2] ...
```

## Configuration Loading Priority

1. Default values from `AppConfig` dataclass
2. Pre-defined YAML configuration file (default: `demo_config.yaml`)
3. Custom YAML file (if `config_path` is specified)
4. Command-line overrides

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
| `api.agent`        | string | `""`          | Pipeline definition for agent API        | `api.agent="react_op"`                                       |

## Operation Configuration

Operations are configured using the pattern `op.{operation_name}.{parameter}`. Each operation can have the following
parameters:

| Parameter                    | Type   | Default Value | Description                                | Example                                                    |
|------------------------------|--------|---------------|--------------------------------------------|------------------------------------------------------------|
| `op.{name}.backend`          | string | `""`          | Backend implementation class name          | `op.build_query_op.backend=build_query_op`                 |
| `op.{name}.prompt_file_path` | string | `""`          | Path to prompt template file               | `op.react_op.prompt_file_path=/path/to/prompt.yaml`        |
| `op.{name}.prompt_dict`      | dict   | `{}`          | Direct prompt configuration dictionary     | `op.react_op.prompt_dict.system="You are an AI assistant"` |
| `op.{name}.llm`              | string | `""`          | Reference to LLM configuration             | `op.react_op.llm=default`                                  |
| `op.{name}.embedding_model`  | string | `""`          | Reference to embedding model configuration | `op.recall_op.embedding_model=default`                     |
| `op.{name}.vector_store`     | string | `""`          | Reference to vector store configuration    | `op.recall_op.vector_store=default`                        |
| `op.{name}.params.{param}`   | any    | `{}`          | Operation-specific parameters              | `op.build_query_op.params.enable_llm_build=false`          |

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

## Complete Example

Here's a complete example showing how to configure the entire system:

```bash
experiencemaker \
  http_service.port=8080 \
  thread_pool.max_workers=20 \
  llm.default.backend=openai_compatible \
  llm.default.model_name=qwen3-32b \
  llm.default.params.temperature=0.6 \
  embedding_model.default.backend=openai_compatible \
  embedding_model.default.model_name=text-embedding-v4 \
  embedding_model.default.params.dimensions=1024 \
  vector_store.default.backend=elasticsearch \
  vector_store.default.embedding_model=default \
```

## Configuration File vs Command Line

You can also create a YAML configuration file and override specific parameters:

1. Create a custom configuration file (`my_config.yaml`)
2. Use it with command-line overrides:

```bash
experiencemaker config_path=my_config.yaml llm.default.model_name=qwen3-32b http_service.port=8080
```

## Parameter Validation

- All parameters are validated according to their types
- Referenced configurations (like `llm`, `embedding_model`, `vector_store`) must exist
- Backend implementations must be registered in their respective registries
- Nested parameters use dot notation for access 