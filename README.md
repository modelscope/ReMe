# ExperienceMaker
<p align="center">
 <img src="cookbook/material/ExperienceMaker.png" alt="ExperienceMakerLogo" width="50%">
</p>

[![](https://img.shields.io/badge/python-3.12+-blue)](https://pypi.org/project/experiencemaker/)
[![](https://img.shields.io/badge/pypi-v0.1.0-blue?logo=pypi)](https://pypi.org/project/experiencemaker/)
[![](https://img.shields.io/badge/license-Apache--2.0-black)](./LICENSE)

----
## 📰 News
- **[2025-08]** We release ExperienceMaker v0.1.0 now, which is also available in [PyPI](https://pypi.org/simple/experiencemaker/)!

----
## 🌟 What is ExperienceMaker?
ExperienceMaker provides agents with robust capabilities for experience generation and reuse. 
By summarizing agents' past trajectories into experiences, it enables these experiences to be applied to subsequent tasks. 
Through the continuous accumulation of experience, agents can keep learning and progressively become more skilled in performing tasks.


### Core Features
- **Experience Generation**: Generate successful or failed experiences by summarizing the agent's historical trajectories.
- **Experience Reuse**: Apply experiences to new tasks by retrieving them from a vector store, helping the agent improve through practice. During RL training, Experience allows the agent to maintain state information, enabling more efficient rollouts.
- **Experience Management**: Provides direct management of experiences, such as loading, dumping, clearing historical experiences, and other flexible database operations.

### Core Advantages
- **Ease of Use**: An HTTP POST interface is provided, allowing one-click startup via the command line. Configuration can be quickly updated using configuration files and command-line arguments.
- **Flexibility**: A rich library of operations is included. By composing atomic ops into pipelines, users can flexibly implement any summarization or retrieval task.
- **Experience Store**: Ready-to-use out of the box — there's no need for you to manually summarize experiences. You can directly leverage existing, comprehensive experience datasets to greatly enhance your agent’s capabilities.
- 
### Framework
- APIs:
  - **Retriever API**: Interface for experience retrieval. The input can be a query or conversation messages, and the output includes a list of retrieved experiences and combined contextual content, aiming to facilitate experience reuse.
  - **Summarizer API**: Interface for experience summarization. The input is a list of agent's historical trajectories, and the output is a list of summarized experiences that have been stored in the vector store.
  - **Vector Store API**: Interface for experience management. The input consists of database operation actions, with optional dump/load paths for experience data import/export.
- Pipeline & Operator: ExperienceMaker abstracts the capabilities of experience summarization and retrieval into atomic functions. By composing these atomic functions into pipelines or adding custom operators, users can easily build any experience summarization or retrieval pipeline.
- Vector Store: ExperienceMaker is equipped with a vector database, with ElasticSearch as the default (due to its excellent performance and ease of use), though it also supports other vector databases.
- LLM & Embedding Model: ExperienceMaker relies on large language models and embedding models to provide text generation and vectorization services. These are the core atomic capabilities of ExperienceMaker.

# install
## Installation
```shell
git clone https://github.com/modelscope/ExperienceMaker.git

# Install the package
pip install .
```

## Install From PyPi
```shell
pip install experiencemaker
```

# Quick Start

## Environment Variables
```shell
export LLM_API_KEY="sk-xxx"
export LLM_BASE_URL="xxx"
export EMBEDDING_MODEL_API_KEY="sk-xxx"
export EMBEDDING_MODEL_BASE_URL="xxx"
```
If you are using Elasticsearch's vector database, you need to add the following environment variables:
```shell
ES_HOSTS=http://0.0.0.0:9200
```

## Start Service
```shell
experiencemaker \
  llm.default.model_name=qwen-max-2025-01-25 \
  embedding_model.default.model_name=text-embedding-v4 \
  vector_store.default.backend=elasticsearch \
```

### Start Vector Store Service(optional)
ExperienceMaker is equipped with a vector database. 
If you just want to try out ExperienceMaker, you can use `backend=local_file` for testing purposes. Please note that this method may become time-consuming when dealing with large amounts of data. You can skip this step.
If you are planning to deploy ExperienceMaker or expect a significant QPS (queries per second), we recommend using `backend=elasticsearch`.
To set up [Elasticsearch](https://www.elastic.co/docs/solutions/search/run-elasticsearch-locally) and Kibana locally, run the start-local script in the command line:
```shell
curl -fsSL https://elastic.co/start-local | sh
```
- Elasticsearch [quick start](./cookbook/)
- chroma
-

## Call Summarizer Service

```python
import json

import requests

base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace1"


def run_summary(messages: list, dump_experience: bool = True):
  response = requests.post(url=base_url + "summarizer", json={
    "workspace_id": workspace_id,
    "traj_list": [
      {"messages": messages, "score": 1.0}
    ]
  })

  if response.status_code != 200:
    print(response.text)
    return

  response = response.json()
  experience_list = response["experience_list"]
  if dump_experience:
    with open("experience.jsonl", "w") as f:
      f.write(json.dumps(experience_list, indent=2, ensure_ascii=False))
```

## Call Summarizer Service

```python
import requests

base_url = "http://0.0.0.0:8001/"
workspace_id = "test_workspace1"


def run_retriever(query: str):
  response = requests.post(url=base_url + "retriever", json={
    "workspace_id": workspace_id,
    "query": query,
  })

  if response.status_code != 200:
    print(response.text)
    return ""

  response = response.json()
  experience_merged: str = response["experience_merged"]
  print(f"experience_merged={experience_merged}")
  return experience_merged
```

For more details, please refer to the simple_demo

## 📖 Citation

Reference to cite if you use `ExperienceMaker` in a paper:
```
@software{
title = {ExperiperienceMaker},
author = {The ExperiperienceMaker Team},
url = {https://github.com/modelscope/ExperiperienceMaker},
month = {08},
year = {2025}
}
```
