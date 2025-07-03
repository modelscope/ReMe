import json

from loguru import logger
from omegaconf import OmegaConf, DictConfig

from v1.schema.app_config import AppConfig


class ConfigParser(object):

    def __init__(self, args: list):
        assert len(args) >= 1, "The `args` require at least one argument."
        assert "config_path=" in args[0], f"The 0th args must be config_path, for example: `config_path=XXX`."
        config_path: str = args[0].replace("config_path=", "")
        yaml_config = OmegaConf.load(config_path)

        self.app_config: DictConfig = OmegaConf.structured(AppConfig)
        self.app_config = OmegaConf.merge(self.app_config, yaml_config)

        if args[1:]:
            cli_config = OmegaConf.from_dotlist(args[1:])
            self.app_config = OmegaConf.merge(self.app_config, cli_config)

        app_config_dict = OmegaConf.to_container(self.app_config, resolve=True)
        app_config_str = json.dumps(app_config_dict, indent=2, ensure_ascii=False)
        logger.info(f"app_config_str={app_config_str}")

    def get_app_config(self, **kwargs) -> AppConfig:
        app_config = self.app_config.copy()
        if kwargs:
            kwargs_list = [f"{k}={v}" for k, v in kwargs.items()]
            update_config = OmegaConf.from_dotlist(kwargs_list)
            app_config = OmegaConf.merge(app_config, update_config)

        return OmegaConf.to_object(app_config)
