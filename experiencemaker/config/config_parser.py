import json
from pathlib import Path

from loguru import logger
from omegaconf import OmegaConf, DictConfig

from experiencemaker.schema.app_config import AppConfig


class ConfigParser:

    def __init__(self, args: list):
        # step1: default config
        self.app_config: DictConfig = OmegaConf.structured(AppConfig)

        # step2: load from config yaml file
        cli_config: DictConfig = OmegaConf.from_dotlist(args)
        temp_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(self.app_config, cli_config))
        if temp_config.config_path:
            config_path = Path(temp_config.config_path)
        else:
            pre_defined_config = temp_config.pre_defined_config
            if not pre_defined_config.endswith(".yaml"):
                pre_defined_config += ".yaml"
            config_path = Path(__file__).parent / pre_defined_config
        logger.info(f"load config from path={config_path}")
        yaml_config = OmegaConf.load(config_path)
        self.app_config = OmegaConf.merge(self.app_config, yaml_config)

        # merge cli config
        self.app_config = OmegaConf.merge(self.app_config, cli_config)

        app_config_dict = OmegaConf.to_container(self.app_config, resolve=True)
        logger.info(f"app_config=\n{json.dumps(app_config_dict, indent=2, ensure_ascii=False)}")

    def get_app_config(self, **kwargs) -> AppConfig:
        app_config = self.app_config.copy()
        if kwargs:
            kwargs_list = [f"{k}={v}" for k, v in kwargs.items()]
            update_config = OmegaConf.from_dotlist(kwargs_list)
            app_config = OmegaConf.merge(app_config, update_config)

        return OmegaConf.to_object(app_config)
