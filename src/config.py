"""
配置管理 — 游戏配置的加载/保存
"""
import json
import os
from typing import cast

import constants

JsonObject = dict[str, object]


def _config_file() -> str:
    """动态读取配置文件路径（方便测试时替换）"""
    return constants.CONFIG_FILE


def load_config() -> dict[str, object]:
    """从文件加载游戏配置，缺失字段自动补全"""
    path = _config_file()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                loaded_text = f.read()
            cfg = cast(object, json.loads(loaded_text))
            if not isinstance(cfg, dict):
                return dict(constants.DEFAULT_CONFIG)
            loaded_cfg = cast(JsonObject, cfg)
            for k, v in constants.DEFAULT_CONFIG.items():
                if k not in loaded_cfg:
                    loaded_cfg[k] = v
            return loaded_cfg
        except Exception:
            pass
    return dict(constants.DEFAULT_CONFIG)


def save_config(cfg: dict[str, object]) -> None:
    """保存游戏配置到文件"""
    with open(_config_file(), "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
