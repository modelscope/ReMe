import argparse
import json
import types
from typing import List

import uvicorn
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel, Field, model_validator

from experiencemaker.utils.util_function import load_env_keys

load_env_keys()

from experiencemaker.model import LLM_REGISTRY, EMBEDDING_MODEL_REGISTRY
from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.module.agent_wrapper import AGENT_WRAPPER_REGISTRY
from experiencemaker.module.agent_wrapper.agent_wrapper_mixin import AgentWrapperMixin
from experiencemaker.module.context_generator import CONTEXT_GENERATOR_REGISTRY
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.module.summarizer import SUMMARIZER_REGISTRY
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from experiencemaker.schema.experience import Experience
from experiencemaker.schema.request import AgentWrapperRequest, ContextGeneratorRequest, SummarizerRequest
from experiencemaker.schema.response import AgentWrapperResponse, ContextGeneratorResponse, SummarizerResponse
from experiencemaker.schema.trajectory import Trajectory, ContextMessage
from experiencemaker.storage import VECTOR_STORE_REGISTRY
from experiencemaker.storage.base_vector_store import BaseVectorStore


class ExperienceMakerService(BaseModel):
    workspace_id: str = Field(default="")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)
    timeout_keep_alive: int = Field(default=600000)
    limit_concurrency: int = Field(default=32)

    llm: BaseLLM | None = Field(default=None)
    embedding_model: BaseEmbeddingModel | None = Field(default=None)
    vector_store: BaseVectorStore | None = Field(default=None)
    agent_wrapper: AgentWrapperMixin | None = Field(default=None)
    context_generator: BaseContextGenerator | None = Field(default=None)
    summarizer: BaseSummarizer | None = Field(default=None)

    @staticmethod
    def init_llm(llm_config: dict) -> BaseLLM:
        backend = llm_config.pop("backend", None)
        assert backend is not None, "llm must have a backend like `openai_compatible`."
        assert backend in LLM_REGISTRY, f"llm backend={backend} not supported. " \
                                        f"supported={LLM_REGISTRY.registered_module_names}"
        llm = LLM_REGISTRY[backend](**llm_config)
        logger.info(f"llm is inited with backend={backend} params={llm_config}")
        return llm

    @classmethod
    def get_llm(cls, config: dict, llm: BaseLLM = None) -> BaseLLM:
        if "llm" in config:
            llm_config = config.pop("llm")
            llm = cls.init_llm(llm_config)
        elif llm is None:
            raise RuntimeError("llm must be provided.")
        return llm

    @staticmethod
    def init_embedding_model(embedding_model_config: dict) -> BaseEmbeddingModel:
        backend = embedding_model_config.pop("backend", None)
        assert backend is not None, "embedding_model must have a backend like `openai_compatible`."
        assert backend in EMBEDDING_MODEL_REGISTRY, f"embedding_model backend={backend} not supported. " \
                                                    f"supported={EMBEDDING_MODEL_REGISTRY.registered_module_names}"
        embedding_model = EMBEDDING_MODEL_REGISTRY[backend](**embedding_model_config)
        logger.info(f"embedding_model is inited with backend={backend} params={embedding_model_config}")
        return embedding_model

    @classmethod
    def get_embedding_model(cls, config: dict, embedding_model: BaseEmbeddingModel = None) -> BaseEmbeddingModel:
        if "embedding_model" in config:
            embedding_model_config = config.pop("embedding_model")
            embedding_model = cls.init_embedding_model(embedding_model_config)
        elif embedding_model is None:
            raise RuntimeError("embedding_model must be provided.")
        return embedding_model

    @classmethod
    def init_vector_store(cls, vector_store_config: dict,
                          embedding_model: BaseEmbeddingModel = None) -> BaseVectorStore:
        backend = vector_store_config.pop("backend", None)
        assert backend is not None, "vector_store must have a backend like `elasticsearch`."
        assert backend in VECTOR_STORE_REGISTRY, f"vector_store backend={backend} not supported. " \
                                                 f"supported={VECTOR_STORE_REGISTRY.registered_module_names}"
        embedding_model = cls.get_embedding_model(vector_store_config, embedding_model=embedding_model)
        vector_store = VECTOR_STORE_REGISTRY[backend](**vector_store_config, embedding_model=embedding_model)
        logger.info(f"vector_store is inited with backend={backend} params={vector_store_config}")
        return vector_store

    @classmethod
    def get_vector_store(cls, config: dict, vector_store: BaseVectorStore = None,
                         embedding_model: BaseEmbeddingModel = None) -> BaseVectorStore:
        if "vector_store" in config:
            vector_store_config = config.pop("vector_store")
            vector_store = cls.init_vector_store(vector_store_config, embedding_model=embedding_model)
        elif vector_store is None:
            raise RuntimeError("vector_store must be provided.")
        return vector_store

    @classmethod
    def init_context_generator(cls, context_generator_config: dict, data: dict) -> BaseContextGenerator:
        backend = context_generator_config.pop("backend", None)
        assert backend is not None, "context_generator must have a backend like `simple`."
        assert backend in CONTEXT_GENERATOR_REGISTRY, f"context_generator backend={backend} not supported. " \
                                                      f"supported={CONTEXT_GENERATOR_REGISTRY.registered_module_names}"

        llm = cls.get_llm(context_generator_config, llm=data.get("llm"))
        vector_store = cls.get_vector_store(context_generator_config, vector_store=data.get("vector_store"),
                                            embedding_model=data.get("embedding_model"))

        context_generator: BaseContextGenerator = CONTEXT_GENERATOR_REGISTRY[backend](
            **context_generator_config, llm=llm, vector_store=vector_store, workspace_id=data.get("workspace_id", ""))
        logger.info(f"context_generator is inited with backend={backend} params={context_generator_config}")
        return context_generator

    @classmethod
    def init_summarizer(cls, summarizer_config: dict, data: dict) -> BaseSummarizer:
        backend = summarizer_config.pop("backend", None)
        assert backend is not None, "summarizer must have a backend like `simple`."
        assert backend in SUMMARIZER_REGISTRY, f"summarizer backend={backend} not supported. " \
                                               f"supported={SUMMARIZER_REGISTRY.registered_module_names}"

        llm = cls.get_llm(summarizer_config, llm=data.get("llm"))
        vector_store = cls.get_vector_store(summarizer_config, vector_store=data.get("vector_store"),
                                            embedding_model=data.get("embedding_model"))
        summarizer: BaseSummarizer = SUMMARIZER_REGISTRY[backend](
            **summarizer_config, llm=llm, vector_store=vector_store, workspace_id=data.get("workspace_id", ""))
        logger.info(f"summarizer is inited with backend={backend} params={summarizer_config}")
        return summarizer

    @classmethod
    def init_agent_wrapper(cls, agent_wrapper_config: dict, data: dict) -> AgentWrapperMixin:
        backend = agent_wrapper_config.pop("backend", None)
        assert backend is not None, "agent_wrapper must have a backend like `simple`."
        assert backend in AGENT_WRAPPER_REGISTRY, f"agent_wrapper backend={backend} not supported. " \
                                                  f"supported={AGENT_WRAPPER_REGISTRY.registered_module_names}"

        llm = cls.get_llm(agent_wrapper_config, llm=data.get("llm"))
        agent_wrapper: AgentWrapperMixin = AGENT_WRAPPER_REGISTRY[backend](
            **agent_wrapper_config, llm=llm, context_generator=data.get("context_generator"),
            workspace_id=data.get("workspace_id", ""))
        logger.info(f"agent_wrapper is inited with backend={backend} params={agent_wrapper_config}")
        return agent_wrapper

    @model_validator(mode="before")  # noqa
    @classmethod
    def init_modules(cls, data: dict):
        try:
            if "llm" in data:
                data["llm"] = cls.init_llm(data["llm"])

            if "embedding_model" in data:
                data["embedding_model"] = cls.init_embedding_model(data["embedding_model"])

            if "vector_store" in data:
                data["vector_store"] = cls.init_vector_store(data["vector_store"],
                                                             embedding_model=data["embedding_model"])

            if "context_generator" in data:
                data["context_generator"] = cls.init_context_generator(data["context_generator"], data)

            if "summarizer" in data:
                data["summarizer"] = cls.init_summarizer(data["summarizer"], data)

            if "agent_wrapper" in data:
                data["agent_wrapper"] = cls.init_agent_wrapper(data["agent_wrapper"], data)
        except Exception as e:
            logger.exception(e.args)
        return data

    def call_agent_wrapper(self, request: AgentWrapperRequest) -> AgentWrapperResponse:
        assert self.agent_wrapper_ is not None, "agent_wrapper must be provided."
        trajectory: Trajectory = self.agent_wrapper_.execute(request.query, **request.metadata)
        return AgentWrapperResponse(trajectory=trajectory)

    def call_context_generator(self, request: ContextGeneratorRequest) -> ContextGeneratorResponse:
        assert self.context_generator_ is not None, "context_generator must be provided."
        context_msg: ContextMessage = self.context_generator_.execute(request.trajectory, **request.metadata)
        return ContextGeneratorResponse(context_msg=context_msg)

    def call_summarizer(self, request: SummarizerRequest) -> SummarizerResponse:
        assert self.summarizer_ is not None, "summarizer must be provided."
        experiences: List[Experience] = self.summarizer_.execute(request.trajectories, request.return_experience,
                                                                 **request.metadata)
        return SummarizerResponse(experiences=experiences)


app = FastAPI()
service: ExperienceMakerService | None = None


@app.post('/agent_wrapper', response_model=AgentWrapperResponse)
def call_agent_wrapper(request: AgentWrapperRequest):
    return service.call_agent_wrapper(request)


@app.post('/context_generator', response_model=ContextGeneratorResponse)
def call_context_generator(request: ContextGeneratorRequest):
    return service.call_context_generator(request)


@app.post('/summarizer', response_model=SummarizerResponse)
def call_summarizer(request: SummarizerRequest):
    return service.call_summarizer(request)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    field_dict = ExperienceMakerService.model_fields
    assert isinstance(field_dict, dict)

    json_keys = []
    for key, info in field_dict.items():
        if info.annotation in [int, str, bool]:
            parser.add_argument(f"--{key}", type=info.annotation, default=info.default)

        elif isinstance(info.annotation, types.UnionType) and issubclass(info.annotation.__args__[0], BaseModel):
            parser.add_argument(f"--{key}", type=str, default=None)
            json_keys.append(key)

        else:
            raise NotImplementedError(f"key={key} annotation={info.annotation} is not supported.")

    args: argparse.Namespace = parser.parse_args()
    service_kwargs = {k: json.loads(v) if k in json_keys else v for k, v in args.__dict__.items()}
    logger.info(f"service.kwargs={json.dumps(service_kwargs, indent=2, ensure_ascii=False)}")

    service = ExperienceMakerService(**service_kwargs)
    uvicorn.run(app,
                host=service.host,
                port=service.port,
                timeout_keep_alive=service.timeout_keep_alive,
                limit_concurrency=service.limit_concurrency)

# launch with:
# python -m experiencemaker.service.experience_maker_service \
#     --port=8001 \
#     --llm='{"backend": "openai_compatible", "model_name": "qwen3-32b", "temperature": 0.6}' \
#     --embedding_model='{"backend": "openai_compatible", "model_name": "text-embedding-v4", "dimensions": 1024}' \
#     --vector_store='{"backend": "elasticsearch", "index_name": "naive_agent"}' \
#     --agent_wrapper='{"backend": "simple", "max_steps": 10}' \
#     --context_generator='{"backend": "simple", "retrieve_top_k": 1}' \
#     --summarizer='{"backend": "simple"}'
