import sys
from concurrent.futures.thread import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI

from v1.config.config_parser import ConfigParser
from v1.em_service import EMService
from v1.schema.request import RetrieverRequest, SummarizerRequest, VectorStoreRequest, AgentRequest
from v1.schema.response import RetrieverResponse, SummarizerResponse, VectorStoreResponse, AgentResponse

app = FastAPI()
config_parser = ConfigParser(sys.argv[1:])
global_app_config = config_parser.get_app_config()
thread_pool: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=global_app_config.thread_pool.max_workers)


@app.post('/retriever', response_model=RetrieverResponse)
def call_retriever(request: RetrieverRequest):
    app_config = config_parser.get_app_config(**request.config)
    ems = EMService(app_config=app_config, thread_pool=thread_pool)
    return ems.call_retriever(request)


@app.post('/summarizer', response_model=SummarizerResponse)
def call_summarizer(request: SummarizerRequest):
    app_config = config_parser.get_app_config(**request.config)
    ems = EMService(app_config=app_config, thread_pool=thread_pool)
    return ems.call_summarizer(request)


@app.post('/vector_store', response_model=VectorStoreResponse)
def call_vector_store(request: VectorStoreRequest):
    app_config = config_parser.get_app_config(**request.config)
    ems = EMService(app_config=app_config, thread_pool=thread_pool)
    return ems.call_vector_store(request)


@app.post('/agent', response_model=AgentResponse)
def call_agent(request: AgentRequest):
    app_config = config_parser.get_app_config(**request.config)
    ems = EMService(app_config=app_config, thread_pool=thread_pool)
    return ems.call_agent(request)


if __name__ == "__main__":
    uvicorn.run(app=app,
                host=global_app_config.http_service.host,
                port=global_app_config.http_service.port,
                timeout_keep_alive=global_app_config.http_service.timeout_keep_alive,
                limit_concurrency=global_app_config.http_service.limit_concurrency,
                workers=global_app_config.http_service.workers)
