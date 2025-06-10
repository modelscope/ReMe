from typing import List

from loguru import logger
from pydantic import BaseModel, Field, model_validator

from experiencemaker.model.base_embedding_model import BaseEmbeddingModel, EMBEDDING_MODEL_REGISTRY
from experiencemaker.model.base_llm import BaseLLM, LLM_REGISTRY
from experiencemaker.module.agent_wrapper.agent_wrapper_mixin import AGENT_WRAPPER_REGISTRY, AgentWrapperMixin
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator, \
    CONTEXT_GENERATOR_REGISTRY
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer, SUMMARIZER_REGISTRY
from experiencemaker.schema.experience import Experience
from experiencemaker.schema.request import AgentWrapperRequest, ContextGeneratorRequest, SummarizerRequest
from experiencemaker.schema.response import AgentWrapperResponse, ContextGeneratorResponse, SummarizerResponse
from experiencemaker.schema.trajectory import Trajectory, ContextMessage
from experiencemaker.storage.base_vector_store import BaseVectorStore, VECTOR_STORE_REGISTRY


class ExperienceMakerService(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)
    timeout_keep_alive: int = Field(default=600000)
    limit_concurrency: int = Field(default=32)

    llm_config: dict = Field(default_factory=dict)
    embedding_model_config: dict = Field(default_factory=dict)
    vector_store_config: dict = Field(default_factory=dict)
    agent_wrapper_config: dict = Field(default_factory=dict)
    context_generator_config: dict = Field(default_factory=dict)
    summarizer_config: dict = Field(default_factory=dict)

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
                                        f"supported={LLM_REGISTRY.registered_modules}"
        llm = LLM_REGISTRY[backend](**llm_config)
        logger.info(f"llm is inited with backend={backend} params={llm_config}")
        return llm

    def get_llm(self, config: dict, llm: BaseLLM = None) -> BaseLLM:
        if "llm" in config:
            llm_config = config.pop("llm")
            llm = self.init_llm(llm_config)
        elif llm is None:
            raise RuntimeError("llm must be provided.")
        return llm

    @staticmethod
    def init_embedding_model(embedding_model_config: dict) -> BaseEmbeddingModel:
        backend = embedding_model_config.pop("backend", None)
        assert backend is not None, "embedding_model must have a backend like `openai_compatible`."
        assert backend in EMBEDDING_MODEL_REGISTRY, f"embedding_model backend={backend} not supported. " \
                                                    f"supported={EMBEDDING_MODEL_REGISTRY.registered_modules}"
        embedding_model = EMBEDDING_MODEL_REGISTRY[backend](**embedding_model_config)
        logger.info(f"embedding_model is inited with backend={backend} params={embedding_model_config}")
        return embedding_model

    def get_embedding_model(self, config: dict, embedding_model: BaseEmbeddingModel = None) -> BaseEmbeddingModel:
        if "embedding_model" in config:
            embedding_model_config = config.pop("embedding_model")
            embedding_model = self.init_embedding_model(embedding_model_config)
        elif embedding_model is None:
            raise RuntimeError("embedding_model must be provided.")
        return embedding_model

    def init_vector_store(self, vector_store_config: dict) -> BaseVectorStore:
        backend = vector_store_config.pop("backend", None)
        assert backend is not None, "vector_store must have a backend like `elasticsearch`."
        assert backend in VECTOR_STORE_REGISTRY, f"vector_store backend={backend} not supported. " \
                                                 f"supported={VECTOR_STORE_REGISTRY.registered_modules}"
        embedding_model = self.get_embedding_model(vector_store_config, embedding_model=self.embedding_model)
        vector_store = VECTOR_STORE_REGISTRY[backend](**vector_store_config, embedding_model=embedding_model)
        logger.info(f"vector_store is inited with backend={backend} params={vector_store_config}")
        return vector_store

    def get_vector_store(self, config: dict, vector_store: BaseVectorStore = None) -> BaseVectorStore:
        if "vector_store" in config:
            vector_store_config = config.pop("vector_store")
            vector_store = self.init_vector_store(vector_store_config)
        elif vector_store is None:
            raise RuntimeError("vector_store must be provided.")
        return vector_store

    def init_context_generator(self, context_generator_config: dict) -> BaseContextGenerator:
        backend = context_generator_config.pop("backend", None)
        assert backend is not None, "context_generator must have a backend like `simple`."
        assert backend in CONTEXT_GENERATOR_REGISTRY, f"context_generator backend={backend} not supported. " \
                                                      f"supported={CONTEXT_GENERATOR_REGISTRY.registered_modules}"
        llm = self.get_llm(context_generator_config, llm=self.llm)
        vector_store = self.get_vector_store(context_generator_config, vector_store=self.vector_store)
        context_generator: BaseContextGenerator = CONTEXT_GENERATOR_REGISTRY[backend](
            **context_generator_config, llm=llm, vector_store=vector_store)
        logger.info(f"context_generator is inited with backend={backend} params={context_generator_config}")
        return context_generator

    def init_summarizer(self, summarizer_config: dict) -> BaseSummarizer:
        backend = summarizer_config.pop("backend", None)
        assert backend is not None, "summarizer must have a backend like `simple`."
        assert backend in SUMMARIZER_REGISTRY, f"summarizer backend={backend} not supported. " \
                                               f"supported={SUMMARIZER_REGISTRY.registered_modules}"
        llm = self.get_llm(summarizer_config, llm=self.llm)
        vector_store = self.get_vector_store(summarizer_config, vector_store=self.vector_store)
        summarizer: BaseSummarizer = SUMMARIZER_REGISTRY[backend](**summarizer_config,
                                                                  llm=llm, vector_store=vector_store)
        logger.info(f"summarizer is inited with backend={backend} params={summarizer_config}")
        return summarizer

    def init_agent_wrapper(self, agent_wrapper_config: dict) -> AgentWrapperMixin:
        backend = agent_wrapper_config.pop("backend", None)
        assert backend is not None, "agent_wrapper must have a backend like `simple`."
        assert backend in AGENT_WRAPPER_REGISTRY, f"agent_wrapper backend={backend} not supported. " \
                                                  f"supported={AGENT_WRAPPER_REGISTRY.registered_modules}"

        llm = self.get_llm(agent_wrapper_config, llm=self.llm)

        agent_wrapper: AgentWrapperMixin = AGENT_WRAPPER_REGISTRY[backend](
            **agent_wrapper_config, llm=llm, context_generator=self.context_generator)
        logger.info(f"agent_wrapper is inited with backend={backend} params={agent_wrapper_config}")
        return agent_wrapper

    @model_validator(mode="after")
    def init_modules(self):
        if self.llm_config:
            self.llm = self.init_llm(self.llm_config)

        if self.embedding_model_config:
            self.embedding_model = self.init_embedding_model(self.embedding_model_config)

        if self.vector_store_config:
            self.vector_store = self.init_vector_store(self.vector_store_config)

        if self.context_generator_config:
            self.context_generator = self.init_context_generator(self.context_generator_config)

        if self.summarizer_config:
            self.summarizer = self.init_summarizer(self.summarizer_config)

        if self.agent_wrapper_config:
            self.agent_wrapper = self.init_agent_wrapper(self.agent_wrapper_config)

    def call_agent_wrapper(self, request: AgentWrapperRequest) -> AgentWrapperResponse:
        assert self.agent_wrapper is not None, "agent_wrapper must be provided."
        trajectory: Trajectory = self.agent_wrapper.execute(request.query, **request.metadata)
        return AgentWrapperResponse(trajectory=trajectory)

    def call_context_generator(self, request: ContextGeneratorRequest) -> ContextGeneratorResponse:
        assert self.context_generator is not None, "context_generator must be provided."
        context_msg: ContextMessage = self.context_generator.execute(request.trajectory, **request.metadata)
        return ContextGeneratorResponse(context_msg=context_msg)

    def call_summarizer(self, request: SummarizerRequest) -> SummarizerResponse:
        assert self.summarizer is not None, "summarizer must be provided."
        experiences: List[Experience] = self.summarizer.execute(request.trajectories, request.return_experience,
                                                                **request.metadata)
        return SummarizerResponse(experiences=experiences)
