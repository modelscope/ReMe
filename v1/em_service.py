from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from v1.pipeline.pipeline import Pipeline
from v1.pipeline.pipeline_context import PipelineContext
from v1.schema.app_config import AppConfig
from v1.schema.request import SummarizerRequest, RetrieverRequest, VectorStoreRequest, AgentRequest
from v1.schema.response import SummarizerResponse, RetrieverResponse, VectorStoreResponse, AgentResponse


class EMService(object):
    def __init__(self, app_config: AppConfig, thread_pool: ThreadPoolExecutor):
        self.context: PipelineContext = PipelineContext(app_config=app_config, thread_pool=thread_pool)

    def __call__(self, service: str, **kwargs) -> dict:
        if service == "retriever":
            response = self.call_retriever(RetrieverRequest(**kwargs))

        elif service == "summarizer":
            response = self.call_summarizer(SummarizerRequest(**kwargs))

        elif service == "vector_store":
            response = self.call_vector_store(VectorStoreRequest(**kwargs))

        elif service == "agent":
            response = self.call_agent(AgentRequest(**kwargs))

        else:
            raise Exception(f"Invalid service={service}")

        return response.model_dump()

    def call_retriever(self, request: RetrieverRequest) -> RetrieverResponse:
        self.context.set_context("request", request)
        response = RetrieverResponse()
        self.context.set_context("response", response)
        try:
            Pipeline(pipeline=self.context.app_config.api.retriever, context=self.context)()
        except Exception as e:
            logger.exception(f"call_retriever encounter error={e.args}")
            response.success = False
            response.metadata["error"] = str(e)
        return response

    def call_summarizer(self, request: SummarizerRequest) -> SummarizerResponse:
        self.context.set_context("request", request)
        response = SummarizerResponse()
        self.context.set_context("request", response)
        try:
            Pipeline(pipeline=self.context.app_config.api.summarizer, context=self.context)()
        except Exception as e:
            logger.exception(f"call_summarizer encounter error={e.args}")
            response.success = False
            response.metadata["error"] = str(e)
        return response

    def call_vector_store(self, request: VectorStoreRequest) -> VectorStoreResponse:
        self.context.set_context("request", request)
        response = VectorStoreResponse()
        self.context.set_context("request", response)
        try:
            Pipeline(pipeline=self.context.app_config.api.vector_store, context=self.context)()
        except Exception as e:
            logger.exception(f"call_vector_store encounter error={e.args}")
            response.success = False
            response.metadata["error"] = str(e)
        return response

    def call_agent(self, request: AgentRequest) -> AgentResponse:
        self.context.set_context("request", request)
        response = AgentResponse()
        self.context.set_context("request", response)
        try:
            Pipeline(pipeline=self.context.app_config.api.agent, context=self.context)()
        except Exception as e:
            logger.exception(f"call_agent encounter error={e.args}")
            response.success = False
            response.metadata["error"] = str(e)
        return response
