"""
配置管理 — 游戏配置的加载/保存
"""
import json
import os
import sys
from typing import cast

import constants

JsonObject = dict[str, object]


def _config_file() -> str:
    """动态读取配置文件路径（方便测试时替换）"""
    return constants.CONFIG_FILE


def _validate_config(cfg: JsonObject) -> JsonObject:
    validated: JsonObject = {}
    for k, default in constants.DEFAULT_CONFIG.items():
        val = cfg.get(k, default)
        if isinstance(default, bool):
            validated[k] = bool(val)
        elif isinstance(default, int):
            try:
                validated[k] = int(val)
            except (ValueError, TypeError):
                validated[k] = default
        elif isinstance(default, list):
            validated[k] = val if isinstance(val, list) else default
        else:
            validated[k] = val if isinstance(val, type(default)) else default
    if isinstance(validated.get("generations"), list) and not validated["generations"]:
        validated["generations"] = list(constants.ALL_GENERATIONS)
    return validated


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
            return _validate_config(loaded_cfg)
        except json.JSONDecodeError:
            print(f"警告: 配置文件损坏，使用默认配置: {path}", file=sys.stderr)
        except OSError as exc:
            print(f"警告: 无法读取配置文件，使用默认配置: {exc}", file=sys.stderr)
    return dict(constants.DEFAULT_CONFIG)


def save_config(cfg: dict[str, object]) -> None:
    """保存游戏配置到文件"""
    try:
        with open(_config_file(), "w") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"警告: 无法保存配置文件: {exc}", file=sys.stderr)
        raise
