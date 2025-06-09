import json
import os
import re
from loguru import logger

def get_html_match_content(content: str, key: str):
    pattern = rf"<{key}>(.*?)</{key}>"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1)
    return None


def load_env_keys():
    if os.path.exists(".env"):
        with open(".env") as f:
            config = json.load(f)
            for k, v in config.items():
                os.environ[k] = v
    else:
        logger.warning(".env file not found~")