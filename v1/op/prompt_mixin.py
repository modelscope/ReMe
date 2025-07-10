from pathlib import Path

import yaml
from loguru import logger


class PromptMixin:

    def __init__(self, file_path: Path | str = None, prompt_dict: dict = None):
        self.prompt_dict: dict = {}
        self.prompt_dict.update(**self.load_prompt_by_file_path(file_path))
        if prompt_dict:
            for key, value in prompt_dict.items():
                if isinstance(value, str):
                    self.prompt_dict[key] = value
                    logger.info(f"add prompt_dict key={key}")

    @staticmethod
    def load_prompt_by_file_path(file_path: Path | str = None):
        prompt_dict = {}
        if file_path is None:
            return prompt_dict

        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            return prompt_dict

        with file_path.open() as f:
            prompt_dict = yaml.load(f, yaml.FullLoader)
            logger.info(f"add prompt_dict keys={prompt_dict.keys()}")
            return prompt_dict

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
