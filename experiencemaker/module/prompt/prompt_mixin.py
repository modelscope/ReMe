from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, Field, model_validator


class PromptMixin(BaseModel):
    prompt_file_path: Path | str = Field(default=None)
    prompt_dict: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def init_prompt(self):
        if self.prompt_dict:
            logger.info(f"load prompt from dict, keys={self.prompt_dict.keys()}")

        if self.prompt_file_path is not None:
            if isinstance(self.prompt_file_path, str):
                self.prompt_file_path = Path(self.prompt_file_path)

            if not self.prompt_file_path.exists():
                logger.warning(f"prompt_file_path={self.prompt_file_path} not exists!")

            else:
                with self.prompt_file_path.open("r") as f:
                    load_prompt_dict = yaml.load(f, yaml.FullLoader)
                    for k, v in load_prompt_dict.items():
                        if k not in self.prompt_dict:
                            self.prompt_dict[k] = v
                            logger.info(f"add prompt_dict key={k}")
                        else:
                            logger.warning(f"key={k} is already exists in prompt_dict!")
        return self

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
