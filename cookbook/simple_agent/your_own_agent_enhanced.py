from loguru import logger
from pydantic import Field, model_validator

from cookbook.simple_agent.your_own_agent import YourOwnAgent
from experiencemaker.em_client import EMClient
from experiencemaker.model import OpenAICompatibleBaseLLM
from experiencemaker.schema.request import ContextGeneratorRequest, SummarizerRequest
from experiencemaker.schema.response import ContextGeneratorResponse, SummarizerResponse
from experiencemaker.schema.trajectory import Trajectory


class YourOwnAgentEnhanced(YourOwnAgent):
    em_client: EMClient | None = Field(default=None)
    workspace_id: str = Field(default=...)

    @model_validator(mode="after")
    def init_client(self):
        self.em_client = EMClient(base_url="http://0.0.0.0:8001")
        return self

    def summary_experience(self, query: str):
        messages = self.run(query)
        trajectory: Trajectory = Trajectory(query=query, steps=messages, answer=messages[-1].content, done=True)

        request: SummarizerRequest = SummarizerRequest(trajectories=[trajectory], workspace_id=self.workspace_id)
        response: SummarizerResponse = self.em_client.call_summarizer(request)
        for experience in response.experiences:
            logger.info(experience.model_dump_json())
        return response.experiences

    def run_with_experience(self, query: str):
        trajectory: Trajectory = Trajectory(query=query)
        request: ContextGeneratorRequest = ContextGeneratorRequest(trajectory=trajectory,
                                                                   retrieve_top_k=1,
                                                                   workspace_id=self.workspace_id)
        response: ContextGeneratorResponse = self.em_client.call_context_generator(request)
        new_query = f"{response.context_msg.content}\n\nUser Question\n{query}"
        logger.info(f"new query={new_query}")
        messages = self.run(new_query)

        trajectory.steps = messages
        trajectory.answer = messages[-1].content
        trajectory.done = True
        trajectory.metadata["experience"] = response.context_msg.content
        return trajectory

    def execute(self):
        self.summary_experience(query="Analyze the company Tesla.")
        self.summary_experience(query="Analyze the company Apple.")

        return self.run_with_experience(query="Analyze Xiaomi Corporation.")


if __name__ == "__main__":
    agent = YourOwnAgentEnhanced(workspace_id="w_agent_enhanced",
                                 llm=OpenAICompatibleBaseLLM(model_name="qwen3-32b", temperature=0.00001))
    traj = agent.execute()
    logger.info(traj.model_dump_json(indent=2))

