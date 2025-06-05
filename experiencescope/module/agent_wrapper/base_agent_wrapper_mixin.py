from abc import ABC

from pydantic import Field, BaseModel

from beyondagent.core.module.base_module import BaseModule
from beyondagent.core.module.context_generator.base_context_generator import BaseContextGenerator
from beyondagent.core.schema.trajectory import Trajectory, ActionMessage, Message


class BaseAgentWrapperMixin(BaseModule, ABC):
    context_generator: BaseContextGenerator | None = Field(default=None)

    def execute(self, query: str, **kwargs) -> Trajectory:
        raise NotImplementedError


class MockAgentWrapper(BaseAgentWrapperMixin):

    def execute(self, query: str, **kwargs) -> Trajectory:
        user_message = Message(content=query)
        answer_message = ActionMessage(content="hello world")

        traj = Trajectory(steps=[user_message, answer_message],
                          done=True,
                          query=query,
                          answer=answer_message.content)
        return traj
