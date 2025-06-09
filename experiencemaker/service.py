from typing import List

import uvicorn
from fastapi import FastAPI
from loguru import logger

from experiencemaker.model import LLM_REGISTRY, EMBEDDING_MODEL_REGISTRY
from experiencemaker.model.base_embedding_model import BaseEmbeddingModel
from experiencemaker.model.base_llm import BaseLLM
from experiencemaker.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from experiencemaker.schema.request import AgentWrapperRequest, ContextGeneratorRequest, SummarizerRequest
from experiencemaker.schema.response import AgentWrapperResponse, ContextGeneratorResponse, SummarizerResponse
from experiencemaker.schema.trajectory import ContextMessage, Trajectory, Sample
from experiencemaker.storage import VECTOR_STORE_REGISTRY
from experiencemaker.storage.base_vector_store import BaseVectorStore

app = FastAPI()
from pydantic import BaseModel, Field, model_validator


class ExperienceMakerHttpService(BaseModel):
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

    agent_wrapper: BaseAgentWrapper | None = Field(default=None)
    context_generator: BaseContextGenerator | None = Field(default=None)
    summarizer: BaseSummarizer | None = Field(default=None)

    @staticmethod
    def init_llm(llm_config: dict):
        backend = llm_config.pop("backend", None)
        assert backend is not None, "llm must have a backend like `openai_compatible`."
        assert backend in LLM_REGISTRY, f"llm backend={backend} not supported. supported backend={LLM_REGISTRY.registered_modules}"
        llm = LLM_REGISTRY[backend](**llm_config)
        logger.info(f"llm is inited with backend={backend} params={llm_config}")
        return llm

    @staticmethod
    def init_embedding_model(embedding_model_config: dict):
        backend = embedding_model_config.pop("backend", None)
        assert backend is not None, "embedding_model must have a backend like `openai_compatible`."
        assert backend in EMBEDDING_MODEL_REGISTRY, f"embedding_model backend={backend} not supported. supported backend={EMBEDDING_MODEL_REGISTRY.registered_modules}"
        embedding_model = EMBEDDING_MODEL_REGISTRY[backend](**embedding_model_config)
        logger.info(f"embedding_model is inited with backend={backend} params={embedding_model_config}")
        return embedding_model

    @staticmethod
    def init_vector_store(vector_store_config: dict):
        backend = vector_store_config.pop("backend", None)
        assert backend is not None, "vector_store must have a backend like `elasticsearch`."
        assert backend in VECTOR_STORE_REGISTRY, f"vector_store backend={backend} not supported. supported backend={VECTOR_STORE_REGISTRY.registered_modules}"
        vector_store = VECTOR_STORE_REGISTRY[backend](**vector_store_config)
        logger.info(f"vector_store is inited with backend={backend} params={vector_store_config}")
        return vector_store

    @model_validator(mode="after")
    def init_modules(self):
        if self.llm_config:
            self.llm = self.init_llm(self.llm_config)

        if self.embedding_model_config:
            self.embedding_model = self.init_embedding_model(self.embedding_model_config)

        if self.vector_store_config:
            self.vector_store = self.init_vector_store(self.vector_store_config)





@app.post('/agent_wrapper', response_model=AgentWrapperResponse)
def call_agent_wrapper(request: AgentWrapperRequest):
    module: BaseAgentWrapper = request.load_from_path()
    trajectory: Trajectory = module.execute(request.query, **request.metadata)
    return AgentWrapperResponse(trajectory=trajectory)


@app.post('/context_generator', response_model=ContextGeneratorResponse)
def call_context_generator(request: ContextGeneratorRequest):
    module: BaseContextGenerator = request.load_from_path()
    context_msg: ContextMessage = module.execute(request.trajectory, **request.metadata)
    return ContextGeneratorResponse(context_msg=context_msg)


@app.post('/summarizer', response_model=SummarizerResponse)
def call_summarizer(request: SummarizerRequest):
    module: BaseSummarizer = request.load_from_path()
    samples: List[Sample] = module.execute(request.trajectories, request.return_samples, **request.metadata)
    return SummarizerResponse(extract_samples=samples)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=600000, limit_concurrency=32)
    # from experiencemaker.config import summarizer_config
    # print(summarizer_config.simple)

    from experiencemaker.config.config_handler import ConfigHandler

    summarizer_config = ConfigHandler(module_name="summarizer")
    context_generator_config = ConfigHandler(module_name="context_generator")
    print(context_generator_config.config_dict)



# launch with:
#   python -m experiencemaker.service.model_service
