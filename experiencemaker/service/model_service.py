from experiencemaker.utils.logger import init_logger
init_logger()

from typing import List
from fastapi import FastAPI
from experiencemaker.module.agent_wrapper.base_agent_wrapper import BaseAgentWrapper
from experiencemaker.module.context_generator.base_context_generator import BaseContextGenerator
from experiencemaker.module.summarizer.base_summarizer import BaseSummarizer
from experiencemaker.schema.request import AgentWrapperRequest, ContextGeneratorRequest, SummarizerRequest
from experiencemaker.schema.response import AgentWrapperResponse, ContextGeneratorResponse, SummarizerResponse
from experiencemaker.schema.trajectory import ContextMessage, Trajectory, Sample
import uvicorn

app = FastAPI()


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

# launch with:
#   python -m experiencemaker.service.model_service
