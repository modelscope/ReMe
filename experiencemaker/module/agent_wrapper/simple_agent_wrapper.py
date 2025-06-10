from experiencemaker.module.agent_wrapper.agent_wrapper_mixin import AgentWrapperMixin, AGENT_WRAPPER_REGISTRY
from experiencemaker.module.agent_wrapper.simple_agent import SimpleAgent
from experiencemaker.schema.trajectory import Trajectory


class SimpleAgentWrapper(SimpleAgent, AgentWrapperMixin):

    def execute(self, query: str, **kwargs) -> Trajectory:
        trajectory = Trajectory(query=query)
        context_msg = self.context_generator.execute(trajectory=trajectory)
        previous_experience = context_msg.content

        messages = self.run(query, previous_experience)

        trajectory.steps = messages
        trajectory.answer = messages[-1].content
        trajectory.done = True
        return trajectory


AGENT_WRAPPER_REGISTRY.register(SimpleAgentWrapper, "simple")
