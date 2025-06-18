from pydantic import Field, BaseModel


class Reward(BaseModel):
    outcome: float = Field(default=0)
    description: str = Field(default="Outcome 1 denotes success, and 0 denotes failure.")
    metadata: dict = Field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.outcome > 0
