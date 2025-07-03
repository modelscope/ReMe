# main.py
# config.py
import json
from dataclasses import dataclass, field, asdict
from typing import List

from omegaconf import OmegaConf


main()

if __name__ == "__main__":
    default_cfg = OmegaConf.structured(AppConfig)

    # 2. 从 YAML 文件加载
    yaml_cfg = OmegaConf.load("config.yaml")

    # 3. 合并（YAML 覆盖默认）
    cfg = OmegaConf.merge(default_cfg, yaml_cfg)

    # 4. 再合并命令行（命令行优先级最高）
    cli_cfg = OmegaConf.from_cli()
    cfg = OmegaConf.merge(cfg, cli_cfg)

    # 5. 转为 dataclass 实例
    cfg_obj: AppConfig = OmegaConf.to_object(cfg)  # 递归转为 dataclass

    print(json.dumps(asdict(cfg_obj), indent=2))
    # print(cfg_obj)  # 如果你需要 dataclass 实例
