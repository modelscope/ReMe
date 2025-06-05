from abc import ABC
from typing import List

from pydantic import BaseModel, Field

from experiencemaker.schema.trajectory import Trajectory


class BaseTrainner(BaseModel, ABC):
    """
    load model/prompt
    data
    env
    -> 新cpt

    off policy/onpolicy
    """
    traj_buffer: List[Trajectory] = Field()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fit(self):
        return

    def save_module_state(self):
        return


class BaseContextTrainner(BaseTrainner):
    """
     load model/prompt/db/buffer -> 新cpt
    """


class BaseSummaryTrainner(BaseTrainner):
    """
     load model/prompt/db/buffer -> 新cpt
    """


class BasePolicyTrainner(BaseTrainner):
    """
     load model/prompt/db/buffer -> 新cpt
    """
