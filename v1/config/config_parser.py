import json
from pathlib import Path

from loguru import logger
from omegaconf import OmegaConf, DictConfig

from v1.schema.app_config import AppConfig


class ConfigParser:
    default_config_name: str = "demo_config.yaml"

    def __init__(self, args: list):
        # step1: default config
        self.app_config: DictConfig = OmegaConf.structured(AppConfig)

        # step2: load from config yaml file
        cli_config: DictConfig = OmegaConf.from_dotlist(args)
        config_path = cli_config.get("config_path")
        if config_path:
            config_path = Path(config_path)
        else:
            config_path = Path(__file__).parent / self.default_config_name
        logger.info(f"load config from path={config_path}")
        yaml_config = OmegaConf.load(config_path)
        self.app_config = OmegaConf.merge(self.app_config, yaml_config)

        # merge cli config
        self.app_config = OmegaConf.merge(self.app_config, cli_config)

        app_config_dict = OmegaConf.to_container(self.app_config, resolve=True)
        logger.info(f"app_config_str={json.dumps(app_config_dict, indent=2, ensure_ascii=False)}")

    def get_app_config(self, **kwargs) -> AppConfig:
        app_config = self.app_config.copy()
        if kwargs:
            kwargs_list = [f"{k}={v}" for k, v in kwargs.items()]
            update_config = OmegaConf.from_dotlist(kwargs_list)
            app_config = OmegaConf.merge(app_config, update_config)

        return OmegaConf.to_object(app_config)
