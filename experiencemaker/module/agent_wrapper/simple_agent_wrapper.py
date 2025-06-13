from experiencemaker.module.agent_wrapper.agent_wrapper_mixin import AgentWrapperMixin, AGENT_WRAPPER_REGISTRY
from experiencemaker.module.agent_wrapper.simple_agent import SimpleAgent
from experiencemaker.schema.trajectory import Trajectory


@AGENT_WRAPPER_REGISTRY.register(name="simple")
class SimpleAgentWrapper(SimpleAgent, AgentWrapperMixin):

    def execute(self, query: str, workspace_id: str = None, **kwargs) -> Trajectory:
        trajectory = Trajectory(query=query)
        context_msg = self.context_generator.execute(trajectory=trajectory, workspace_id=workspace_id)
        new_query = f"{context_msg.content}\n\nUser Question\n{query}"

        messages = self.run(new_query)

        trajectory.steps = messages
        trajectory.answer = messages[-1].content
        trajectory.done = True
        return trajectory
