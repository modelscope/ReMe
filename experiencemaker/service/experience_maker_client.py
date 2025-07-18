from pydantic import Field

from experiencemaker.schema.message import Trajectory, Message
from experiencemaker.schema.request import RetrieverRequest, SummarizerRequest, VectorStoreRequest, AgentRequest
from experiencemaker.schema.response import RetrieverResponse, SummarizerResponse, VectorStoreResponse, AgentResponse
from experiencemaker.utils.http_client import HttpClient


class ExperienceMakerClient(HttpClient):
    base_url: str = Field(default="http://0.0.0.0:8001")

    def call_retriever(self, request: RetrieverRequest):
        self.url = self.base_url + "/retriever"
        return RetrieverResponse(**self.request(json_data=request.model_dump()))

    def call_summarizer(self, request: SummarizerRequest):
        self.url = self.base_url + "/summarizer"
        return SummarizerResponse(**self.request(json_data=request.model_dump()))

    def call_vector_store(self, request: VectorStoreRequest):
        self.url = self.base_url + "/vector_store"
        return VectorStoreResponse(**self.request(json_data=request.model_dump()))

    def call_agent(self, request: AgentRequest):
        self.url = self.base_url + "/agent"
        return AgentResponse(**self.request(json_data=request.model_dump()))


if __name__ == "__main__":
    client = ExperienceMakerClient()
    workspace_id = "t123"
    response = client.call_summarizer(
        SummarizerRequest(workspace_id=workspace_id,
                          traj_list=[Trajectory(messages=[Message(content="hello world!")])]))
    print(response.model_dump())
    response = client.call_retriever(RetrieverRequest(workspace_id=workspace_id, query="hello world"))
    print(response.model_dump())
