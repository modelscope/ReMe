from experiencemaker.module.agent_wrapper.agent_wrapper_mixin import AgentWrapperMixin
from experiencemaker.module.agent_wrapper.simple_agent_wrapper import SimpleAgentWrapper
from experiencemaker.utils.registry import Registry

AGENT_WRAPPER_REGISTRY = Registry[AgentWrapperMixin]("agent_wrapper")

AGENT_WRAPPER_REGISTRY.register(SimpleAgentWrapper, "simple")
