import json
from pathlib import Path

from loguru import logger
from omegaconf import OmegaConf, DictConfig

from experiencemaker.schema.app_config import AppConfig


class ConfigParser:
    """
    Configuration parser that handles loading and merging configurations from multiple sources.
    
    The configuration loading priority (from lowest to highest):
    1. Default configuration from AppConfig schema
    2. YAML configuration file
    3. Command line arguments
    4. Runtime keyword arguments
    """

    def __init__(self, args: list):
        """
        Initialize the configuration parser with command line arguments.
        
        Args:
            args: List of command line arguments in dotlist format (e.g., ['key=value'])
        """
        # Step 1: Initialize with default configuration from AppConfig schema
        self.app_config: DictConfig = OmegaConf.structured(AppConfig)

        # Step 2: Load configuration from YAML file
        # First, parse CLI arguments to check if custom config path is specified
        cli_config: DictConfig = OmegaConf.from_dotlist(args)
        temp_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(self.app_config, cli_config))
        
        # Determine config file path: either from CLI args or use predefined config
        if temp_config.config_path:
            # Use custom config path if provided
            config_path = Path(temp_config.config_path)
        else:
            # Use predefined config name from the config directory
            pre_defined_config = temp_config.pre_defined_config
            if not pre_defined_config.endswith(".yaml"):
                pre_defined_config += ".yaml"
            config_path = Path(__file__).parent / pre_defined_config
            
        logger.info(f"load config from path={config_path}")
        yaml_config = OmegaConf.load(config_path)
        # Merge YAML config with default config
        self.app_config = OmegaConf.merge(self.app_config, yaml_config)

        # Step 3: Merge CLI arguments (highest priority)
        self.app_config = OmegaConf.merge(self.app_config, cli_config)

        # Log the final merged configuration
        app_config_dict = OmegaConf.to_container(self.app_config, resolve=True)
        logger.info(f"app_config=\n{json.dumps(app_config_dict, indent=2, ensure_ascii=False)}")

    def get_app_config(self, **kwargs) -> AppConfig:
        """
        Get the application configuration with optional runtime overrides.
        
        Args:
            **kwargs: Additional configuration parameters to override at runtime
            
        Returns:
            AppConfig: The final application configuration object
        """
        # Create a copy of the current configuration
        app_config = self.app_config.copy()
        
        # Apply runtime overrides if provided
        if kwargs:
            # Convert kwargs to dotlist format for OmegaConf
            kwargs_list = [f"{k}={v}" for k, v in kwargs.items()]
            update_config = OmegaConf.from_dotlist(kwargs_list)
            app_config = OmegaConf.merge(app_config, update_config)

        # Convert OmegaConf DictConfig to structured AppConfig object
        return OmegaConf.to_object(app_config)
