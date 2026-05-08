"""
模糊匹配与补全 — 宝可梦查找 + prompt_toolkit 补全器
"""
from __future__ import annotations

from typing import Any, TypedDict, cast, override

from constants import GEN_MAP, TYPE_COLORS, FORM_INDICATORS
from data import build_pokemon_index


TYPE_CN_TO_EN_MAP = {
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


class PokemonEntry(TypedDict, total=False):
    id: int
    name: str
    name_en: str
    name_jp: str
    types: list[str]
    generation: str


PokemonIndex = dict[int | str, PokemonEntry]
IdMap = dict[int, list[PokemonEntry]]

_pokemon_index: PokemonIndex | None = None
_id_map: IdMap | None = None


def _get_index(pokemon_list: list[PokemonEntry]) -> tuple[PokemonIndex, IdMap]:
    global _pokemon_index, _id_map
    if _pokemon_index is None or _id_map is None:
        _pokemon_index, _id_map = build_pokemon_index(cast(list[dict[str, object]], pokemon_list))
        _pokemon_index = cast(PokemonIndex, _pokemon_index)
    return _pokemon_index, _id_map


def score_pokemon(query: str, p: PokemonEntry) -> int:
    """给宝可梦打分：query 与 name 的匹配程度，分数越高越相关"""
    q = query.lower().strip()
    name_en = p["name_en"].lower().replace("-", "").replace(" ", "")
    name_cn = p["name"]
    name_jp = p.get("name_jp", "").lower()
    poke_id = str(p["id"])

    # 编号精确匹配
    if q == poke_id or q == f"#{poke_id}":
        return 100
    # 编号前缀
    if poke_id.startswith(q.lstrip("#")) and len(q) >= 2:
        return 90
    # 中文名精确（优先完整匹配，包括地区形态）
    if name_cn == q:
        return 100
    # 英文名精确
    if name_en == q:
        return 100
    # 日文名精确
    if name_jp and name_jp == q:
        return 100
    # 中文名前缀（完整匹配地区形态标识）
    if name_cn.startswith(q) and len(q) >= 1:
        # 如果用户输入包含地区标识，给予更高分数
        if any(kw in q for kw in FORM_INDICATORS):
            return 95
        return 85
    # 英文名前缀
    if name_en.startswith(q):
        return 80
    # 日文名前缀
    if name_jp and name_jp.startswith(q):
        return 78
    # 中文名包含
    if q in name_cn and len(q) >= 2:
        return 70
    # 英文名包含
    if q in name_en and len(q) >= 3:
        return 60
    # 编号接近
    try:
        if abs(int(q) - p["id"]) <= 2 and q.isdigit():
            return 50
    except ValueError:
        pass
    # 乱序字符匹配 (容忍 typo)
    if len(q) >= 3:
        en_clean = name_en
        q_idx = 0
        for ch in en_clean:
            if q_idx < len(q) and q[q_idx] == ch:
                q_idx += 1
        if q_idx >= len(q) - 1:
            return 40
    return 0


def get_fuzzy_matches(query: str, pokemon_list: list[PokemonEntry], limit: int = 15) -> list[PokemonEntry]:
    """返回按匹配度排序的模糊匹配结果"""
    q = query.strip()
    if not q:
        return []
    scored = []
    for p in pokemon_list:
        s = score_pokemon(q, p)
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]


def find_pokemon(query: str, pokemon_list: list[PokemonEntry]) -> PokemonEntry | None:
    """精确查找宝可梦（中英文名、编号），找不到则取最佳模糊匹配
    
    对于地区形态（共享相同编号），会通过名称进一步区分：
    - 如果输入包含 FORM_INDICATORS 中的标识符，优先匹配地区形态
    - 否则匹配原版形态
    """
    q = query.strip().lower()
    query_raw = query.strip()
    idx, id_map = _get_index(pokemon_list)

    # 检查是否有形态标识符（用于地区形态区分）
    has_form_indicator = any(kw in query_raw for kw in FORM_INDICATORS)

    # O(1) exact lookups by ID
    # 先尝试提取数字 ID（支持 "26" 或 "26-阿罗拉的样子" 格式）
    num_str = ""
    for ch in q.lstrip("#"):
        if ch.isdigit():
            num_str += ch
        else:
            break
    
    if num_str:
        try:
            num = int(num_str)
            if num in id_map:
                candidates = id_map[num]
                if len(candidates) == 1:
                    return candidates[0]
                # 多个候选（地区形态），通过名称区分
                if has_form_indicator:
                    # 尝试精确匹配用户输入的具体形态（通过形态标识符）
                    for p in candidates:
                        if "-" in p["name"]:
                            # 提取形态名称（如 "阿罗拉的样子", "伽勒尔的样子"）
                            form_part = p["name"].split("-", 1)[1] if "-" in p["name"] else ""
                            # 检查用户查询是否包含这个形态标识符
                            if form_part and form_part in query_raw:
                                return p
                    # 如果没有精确匹配，返回任意一个地区形态（名称包含 "-" 的）
                    for p in candidates:
                        if "-" in p["name"]:
                            return p
                # 否则返回第一个（通常是原版）
                return candidates[0]
        except ValueError:
            pass

    # Exact lookup by Chinese name
    if query.strip() in idx:
        return idx[query.strip()]

    # Exact lookup by English name (normalized)
    en_key = q.replace("-", "").replace(" ", "")
    if en_key in idx:
        return idx[en_key]

    # Fallback to fuzzy matching for partial/typo queries
    matches = get_fuzzy_matches(query, pokemon_list, limit=1)
    return matches[0] if matches else None


# ══════════════════════════════════════════════
#  prompt_toolkit 补全器
# ══════════════════════════════════════════════

try:
    from prompt_toolkit.completion import Completion, Completer

    class PokemonCompleter(Completer):
        """prompt_toolkit 模糊补全器 — 输入时弹出候选列表"""

        def __init__(self, pokemon_list: list[PokemonEntry]) -> None:
            self.pokemon_list = pokemon_list

        @override
        def get_completions(self, document: Any, complete_event: Any):
            text = document.text_before_cursor
            words = text.rstrip().split()
            if not words:
                return
            query = words[-1] if text and not text.endswith(" ") else ""
            if not query:
                return

            matches = get_fuzzy_matches(query, self.pokemon_list, limit=15)
            for p in matches:
                types_str = "/".join(p["types"])
                primary_type = p["types"][0] if p.get("types") else ""
                type_key = TYPE_CN_TO_EN_MAP.get(primary_type, "")
                type_color = TYPE_COLORS.get(type_key, "")
                gen_str = GEN_MAP.get(p["generation"], (p["generation"],))[0]
                display_text = f"{p['name']} ({p['name_en']}) #{p['id']:04d}"
                type_indicator = f"[{types_str}]"
                if type_color:
                    type_indicator = f"[{types_str}|{type_color}]"
                meta = f"{type_indicator} · {gen_str}"
                yield Completion(
                    text=p["name"],
                    start_position=-len(query),
                    display=display_text,
                    display_meta=meta,
                )

except ImportError:
    pass
