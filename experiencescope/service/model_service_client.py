from pydantic import Field

from experiencescope.schema.request import AgentWrapperRequest, ContextGeneratorRequest, SummarizerRequest
from experiencescope.schema.response import AgentWrapperResponse, ContextGeneratorResponse, SummarizerResponse
from experiencescope.utils.http_client import HttpClient


class ModelServiceClient(HttpClient):
    base_url: str = Field(default=...)

    def call_agent_wrapper(self, request: AgentWrapperRequest):
        self.url = self.base_url + "/agent_wrapper"
        return AgentWrapperResponse(**self.request(json_data=request.model_dump(),
                                                   headers={"Content-Type": "application/json"}))

    def call_context_generator(self, request: ContextGeneratorRequest):
        self.url = self.base_url + "/context_generator"
        return ContextGeneratorResponse(**self.request(json_data=request.model_dump(),
                                                       headers={"Content-Type": "application/json"}))

    def call_summarizer(self, request: SummarizerRequest):
        self.url = self.base_url + "/summarizer"
        return SummarizerResponse(**self.request(json_data=request.model_dump(),
                                                 headers={"Content-Type": "application/json"}))
