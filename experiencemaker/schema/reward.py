from pydantic import Field, BaseModel


class Reward(BaseModel):
    reward_value: float | None = Field(default=None)
    metadata: dict = Field(default_factory=dict)
