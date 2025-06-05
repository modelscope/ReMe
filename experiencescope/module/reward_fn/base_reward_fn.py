from abc import ABC

from beyondagent.core.module.base_module import BaseModule
from beyondagent.core.schema.reward import Reward
from beyondagent.core.schema.trajectory import Trajectory


class BaseRewardFn(BaseModule, ABC):

    def execute(self, trajectory: Trajectory, ground_truth=None, **kwargs) -> Reward:
        raise NotImplementedError
