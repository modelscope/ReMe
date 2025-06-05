from abc import ABC

from experiencescope.module.base_module import BaseModule
from experiencescope.schema.reward import Reward
from experiencescope.schema.trajectory import Trajectory


class BaseRewardFn(BaseModule, ABC):

    def execute(self, trajectory: Trajectory, ground_truth=None, **kwargs) -> Reward:
        raise NotImplementedError
