from flowllm.config.pydantic_config_parser import PydanticConfigParser


class ConfigParser(PydanticConfigParser):
    current_file: str = __file__
    default_config_name: str = "default"
