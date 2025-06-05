import os

import yaml
from loguru import logger
from pydantic import BaseModel, Field


class PromptHandler(BaseModel):
    dir_path: str = Field(default="")
    prompt_dict: dict = Field(default_factory=dict)

    def add_prompt_file(self, file_name: str):
        prompt_path = os.path.join(self.dir_path, file_name + ".yaml")
        self._add_prompt_file(prompt_path)

    def _add_prompt_file(self, prompt_path: str):
        if os.path.exists(prompt_path):
            with open(prompt_path) as f:
                prompt_dict: dict = yaml.load(f, yaml.FullLoader)
            self.update_prompt_dict(prompt_dict)
        else:
            logger.warning(f"prompt_path={prompt_path} not exists!")

    def update_prompt_dict(self, prompt_dict: dict):
        self.prompt_dict.update(prompt_dict)

    def __getitem__(self, key: str):
        return self.prompt_dict[key]

    def __setitem__(self, key: str, value: str):
        self.prompt_dict[key] = value

    def __getattr__(self, key: str):
        if key in self.prompt_dict:
            return self.prompt_dict[key]

        return super().__getattr__(key)

    def prompt_format(self, prompt_name: str, **kwargs):
        prompt = self.prompt_dict[prompt_name]

        flag_kwargs = {k: v for k, v in kwargs.items() if isinstance(v, bool)}
        other_kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, bool)}

        if flag_kwargs:
            split_prompt = []
            for line in prompt.strip().split("\n"):
                hit = False
                hit_flag = True
                for key, flag in kwargs.items():
                    if not line.startswith(f"[{key}]"):
                        continue

                    else:
                        hit = True
                        hit_flag = flag
                        line = line.strip(f"[{key}]")
                        break

                if not hit:
                    split_prompt.append(line)
                elif hit_flag:
                    split_prompt.append(line)

            prompt = "\n".join(split_prompt)

        if other_kwargs:
            prompt = prompt.format(**other_kwargs)

        return prompt
