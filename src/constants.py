"""
常量定义 — 属性映射、世代映射、默认配置、路径
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

from .paths import PROJECT_DIR, DATA_FILE, CACHE_DIR, STATS_FILE, CONFIG_FILE  # noqa: F401


class Hint(NamedTuple):
    label: str
    value: str
    level: str
    arrow: Optional[str] = None

# ── 属性中文→英文映射 ──
TYPE_CN_TO_EN_MAP: Dict[str, str] = {
    "一般": "normal",
    "火": "fire",
    "水": "water",
    "草": "grass",
    "电": "electric",
    "冰": "ice",
    "格斗": "fighting",
    "毒": "poison",
    "地面": "ground",
    "飞行": "flying",
    "超能力": "psychic",
    "虫": "bug",
    "岩石": "rock",
    "幽灵": "ghost",
    "龙": "dragon",
    "恶": "dark",
    "钢": "steel",
    "妖精": "fairy",
}

# ── 属性颜色 (ANSI hex) ──
TYPE_COLORS: Dict[str, str] = {
    "normal": "#A8A878", "fire": "#F08030", "water": "#6890F0",
    "grass": "#78C850", "electric": "#F8D030", "ice": "#98D8D8",
    "fighting": "#C03028", "poison": "#A040A0", "ground": "#E0C068",
    "flying": "#A890F0", "psychic": "#F85888", "bug": "#A8B820",
    "rock": "#B8A038", "ghost": "#705898", "dragon": "#7038F8",
    "dark": "#705848", "steel": "#B8B8D0", "fairy": "#EE99AC",
}

# ── 世代名称 → (缩写, 序号) ──
GEN_MAP: Dict[str, Tuple[str, int]] = {
    "第一世代": ("1代", 1), "第二世代": ("2代", 2), "第三世代": ("3代", 3),
    "第四世代": ("4代", 4), "第五世代": ("5代", 5), "第六世代": ("6代", 6),
    "第七世代": ("7代", 7), "第八世代": ("8代", 8), "第九世代": ("9代", 9),
}

# ── 所有世代名列表 (固定顺序) ──
ALL_GENERATIONS: List[str] = [
    "第一世代", "第二世代", "第三世代", "第四世代",
    "第五世代", "第六世代", "第七世代", "第八世代", "第九世代",
]

# ── 默认游戏配置 ──
GAME_MODE_PRESETS: Dict[str, dict] = {
    "easy": {"id_range": 30, "stat_range": 50, "speed_range": 25, "detail_range": 20, "height_range": 10, "weight_range": 60, "default_guesses": 15},
    "normal": {"id_range": 10, "stat_range": 30, "speed_range": 15, "detail_range": 10, "height_range": 5, "weight_range": 30, "default_guesses": 10},
    "hard": {"id_range": 5, "stat_range": 15, "speed_range": 8, "detail_range": 5, "height_range": 3, "weight_range": 15, "default_guesses": 7},
}

DEFAULT_CONFIG: Dict[str, object] = {
    "game_mode": "normal",
    "generations": list(ALL_GENERATIONS),
    "max_guesses": 10,
    "show_more_stats": False,
    "show_more_appearance": False,
    "show_egg_group": False,
    "show_gen_arrow": True,
    "reverse_order": False,
    "mischief": False,
}
