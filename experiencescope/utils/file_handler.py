import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, PrivateAttr


class FileHandler(BaseModel):
    file_path: str = Field(default=...)
    _obj: Any = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        suffix = Path(self.file_path).suffix
        if suffix == ".json":
            self._obj = json
        elif suffix == ".yaml":
            self._obj = yaml
        else:
            raise ValueError(f"unsupported file type={suffix}")

    def dump(self, config, **kwargs):
        with open(self.file_path, "w") as f:
            self._obj.dump(config, f, **kwargs)

    def load(self, **kwargs):
        with open(self.file_path, "r") as f:
            return self._obj.load(f, **kwargs)
