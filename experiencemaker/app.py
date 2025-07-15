import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from experiencemaker.schema.request import RetrieverRequest, SummarizerRequest, VectorStoreRequest, AgentRequest
from experiencemaker.schema.response import RetrieverResponse, SummarizerResponse, VectorStoreResponse, AgentResponse
from experiencemaker.service.experience_maker_service import ExperienceMakerService

load_dotenv()

app = FastAPI()
service = ExperienceMakerService(sys.argv[1:])

@app.post('/retriever', response_model=RetrieverResponse)
def call_retriever(request: RetrieverRequest):
    return service(api="retriever", request=request)


@app.post('/summarizer', response_model=SummarizerResponse)
def call_summarizer(request: SummarizerRequest):
    return service(api="summarizer", request=request)


@app.post('/vector_store', response_model=VectorStoreResponse)
def call_vector_store(request: VectorStoreRequest):
    return service(api="vector_store", request=request)


@app.post('/agent', response_model=AgentResponse)
def call_agent(request: AgentRequest):
    return service(api="agent", request=request)


def main():
    uvicorn.run(app=app,
                host=service.http_service_config.host,
                port=service.http_service_config.port,
                timeout_keep_alive=service.http_service_config.timeout_keep_alive,
                limit_concurrency=service.http_service_config.limit_concurrency)


if __name__ == "__main__":
    main()
