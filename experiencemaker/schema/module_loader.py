from importlib import import_module

from pydantic import BaseModel, Field

from experiencemaker.utils.file_handler import FileHandler


class ModuleLoader(BaseModel):
    class_path: str = Field(default=...)
    class_name: str = Field(default=...)
    config_path: str = Field(default="")
    config: dict = Field(default_factory=dict)

    def load_from_config(self):
        return getattr(import_module(self.class_path), self.class_name)(**self.config)

    def load_from_path(self):
        self.config = FileHandler(file_path=self.config_path).load()
        return self.load_from_config()
