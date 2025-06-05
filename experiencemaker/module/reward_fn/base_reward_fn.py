from abc import ABC

from experiencemaker.module.base_module import BaseModule
from experiencemaker.schema.reward import Reward
from experiencemaker.schema.trajectory import Trajectory


class BaseRewardFn(BaseModule, ABC):

    def execute(self, trajectory: Trajectory, ground_truth=None, **kwargs) -> Reward:
        raise NotImplementedError
