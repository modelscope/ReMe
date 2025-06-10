from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.trajectory import Trajectory


class BaseTrainner(BaseModel, ABC):
    traj_buffer: List[Trajectory] = Field()

    def fit(self):
        return

    def save_module_state(self):
        return


class BaseContextTrainner(BaseTrainner):
    """
    load model/prompt/db/buffer -> new cpt
    """


class BaseSummaryTrainner(BaseTrainner):
    """
    load model/prompt/db/buffer -> new cpt
    """


class BasePolicyTrainner(BaseTrainner):
    """
    load model/prompt/db/buffer -> new cpt
    """
