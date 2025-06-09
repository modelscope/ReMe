from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from experiencemaker.utils.file_handler import FileHandler


class ConfigHandler(BaseModel):
    module_name: str = Field(default=...)
    config_dict: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def register_config(self):
        module_config_path: Path = Path(__file__).parent / self.module_name
        for config_path in module_config_path.iterdir():
            config_name = config_path.stem
            config = FileHandler(file_path=config_path).load()
            self.config_dict[config_name] = config
        return self

    def list_config_names(self):
        return list(self.config_dict.keys())

    def __getattr__(self, item):
        if item in self.config_dict:
            return self.config_dict[item]
        return super().__getattr__(item)

    def __getitem__(self, item):
        if item in self.config_dict:
            return self.config_dict[item]
        return super().__getitem__(item)
