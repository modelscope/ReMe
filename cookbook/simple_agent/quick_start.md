# Quick Start

## Hello Experience Maker
Here is a simple user guide for ExperienceMaker.

### Step0: Preparation Work

#### Prepare LLM & EMBEDDING_MODEL
We need to prepare the API services for the LLM and the Embedding model. 
Since we are using an OpenAI-compatible service, we only need to write the `OPENAI_API_KEY` and `OPENAI_BASE_URL` into the environment.
```shell
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="xxx"
```

#### Prepare Vector Store
If you want to use vector store, you need to set up a vector database. Don't forget to set up the `ES_HOSTS`.
- Elasticsearch [quick start](../vector_store/elasticsearch.md)

#### Prepare Your Own Agent
Assume you have a runnable agent.
Here, we use a basic LLM combined with a simple react framework including three tools(code, web_search, terminate) as an example.
```python
class YourOwnAgent(...):
    ...
    def think(self, **kwargs) -> bool:
        ...

    def act(self, **kwargs):
        ...    

    def run(self, query: str, previous_experience: str):
        ...
```

Here is an [example code](./your_own_agent.py) with [prompt](./your_own_agent_prompt.yaml). To use this simple agent, you will need to set up `DASHSCOPE_API_KEY`.
```shell
export DASHSCOPE_API_KEY="sk-xxx"
```

### Step1: Start Experience Maker Http Service
- Install dependencies.
```shell
pip install .
```

- We start our context and summary services in `simple` mode. Next, you can use standard HTTP interfaces to call the services.
```shell
pip install .
python -m experiencemaker.em_service \
 --port=8001 \
 --llm='{"backend": "openai_compatible", "model_name": "qwen3-32b", "temperature": 0.6}' \
 --embedding_model='{"backend": "openai_compatible", "model_name": "text-embedding-v4", "dimensions": 1024}' \
 --vector_store='{"backend": "elasticsearch"}' \
 --context_generator='{"backend": "simple"}' \
 --summarizer='{"backend": "simple"}'
```
