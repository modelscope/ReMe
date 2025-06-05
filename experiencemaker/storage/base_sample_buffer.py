from typing import List

from pydantic import BaseModel

from experiencemaker.schema.trajectory import Sample


class BaseSampleBuffer(BaseModel):

    def add(self, samples: Sample | List[Sample]):
        raise NotImplementedError

    def get_all(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError
