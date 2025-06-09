from abc import ABC

from pydantic import BaseModel

from experiencemaker.schema.reward import Reward
from experiencemaker.schema.trajectory import Trajectory


class BaseRewardFn(BaseModel, ABC):

    def execute(self, trajectory: Trajectory = None, ground_truth=None, **kwargs) -> Reward:
        raise NotImplementedError
