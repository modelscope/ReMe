import argparse
import json

import uvicorn
from fastapi import FastAPI

from experiencemaker.schema.request import AgentWrapperRequest, ContextGeneratorRequest, SummarizerRequest
from experiencemaker.schema.response import AgentWrapperResponse, ContextGeneratorResponse, SummarizerResponse
from experiencemaker.service.experience_maker_service import ExperienceMakerService
from experiencemaker.utils.file_handler import FileHandler

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


# launch with: python -m experiencemaker.service.http_service

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, help='config dict')
    parser.add_argument('--config_path', type=str, help='config load path')
    args = parser.parse_args()

    if args.config_path:
        config = FileHandler(file_path=args.config_path).load()
    elif args.config:
        config = json.loads(args.config)
    else:
        raise RuntimeError("both config and config_path are not specified")

    service = ExperienceMakerService(**config)
    uvicorn.run(app,
                host=service.host,
                port=service.port,
                timeout_keep_alive=service.timeout_keep_alive,
                limit_concurrency=service.limit_concurrency)
