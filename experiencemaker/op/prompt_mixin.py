from pathlib import Path

import yaml
from loguru import logger


class PromptMixin:

    def __init__(self):
        self._prompt_dict: dict = {}

    def load_prompt_by_file(self, prompt_file_path: Path | str = None):
        if prompt_file_path is None:
            return

        if isinstance(prompt_file_path, str):
            prompt_file_path = Path(prompt_file_path)

        if not prompt_file_path.exists():
            return

        with prompt_file_path.open() as f:
            prompt_dict = yaml.load(f, yaml.FullLoader)
            self.load_prompt_dict(prompt_dict)

    def load_prompt_dict(self, prompt_dict: dict = None):
        if not prompt_dict:
            return

        for key, value in prompt_dict.items():
            if isinstance(value, str):
                if key in self._prompt_dict:
                    self._prompt_dict[key] = value
                    logger.warning(f"prompt_dict key={key} overwrite!")

                else:
                    self._prompt_dict[key] = value
                    logger.info(f"add prompt_dict key={key}")

    def prompt_format(self, prompt_name: str, **kwargs):
        prompt = self._prompt_dict[prompt_name]

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

    def get_prompt(self, key: str):
        return self._prompt_dict[key]
