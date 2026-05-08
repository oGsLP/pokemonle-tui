"""
模糊匹配与补全 — 宝可梦查找 + prompt_toolkit 补全器
"""
from __future__ import annotations

from typing import Any, cast, override

from constants import GEN_MAP, TYPE_COLORS, TYPE_CN_TO_EN_MAP
from data import build_pokemon_index
from poketypes import PokemonEntry


def score_pokemon(query: str, p: PokemonEntry) -> int:
    """给宝可梦打分：query 与 name 的匹配程度，分数越高越相关"""
    q = query.lower().strip()
    name_en_norm: str = p.get("_name_en_norm", p["name_en"].lower().replace("-", "").replace(" ", ""))
    name_cn = p["name"]
    name_jp_norm: str = p.get("_name_jp_norm", p.get("name_jp", "").lower())
    poke_id = p.get("_id_str", str(p["id"]))

    # 编号精确匹配
    if q == poke_id or q == f"#{poke_id}":
        return 100
    # 编号前缀
    if poke_id.startswith(q.lstrip("#")) and len(q) >= 2:
        return 90
    # 中文名精确
    if name_cn == q:
        return 100
    # 英文名精确
    if name_en_norm == q:
        return 100
    # 日文名精确
    if name_jp_norm and name_jp_norm == q:
        return 100
    # 中文名前缀
    if name_cn.startswith(q) and len(q) >= 1:
        return 85
    # 英文名前缀
    if name_en_norm.startswith(q):
        return 80
    # 日文名前缀
    if name_jp_norm and name_jp_norm.startswith(q):
        return 78
    # 中文名包含
    if q in name_cn and len(q) >= 2:
        return 70
    # 英文名包含
    if q in name_en_norm and len(q) >= 3:
        return 60
    # 编号接近
    try:
        if abs(int(q) - p["id"]) <= 2 and q.isdigit():
            return 50
    except ValueError:
        pass
    # 乱序字符匹配 (容忍 typo)
    if len(q) >= 3:
        q_idx = 0
        for ch in name_en_norm:
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


def find_pokemon(query: str, pokemon_list: list[PokemonEntry], index: dict[object, PokemonEntry] | None = None) -> PokemonEntry | None:
    """精确查找宝可梦（中英文名、编号），找不到则取最佳模糊匹配"""
    q = query.strip().lower()
    idx = cast(dict[object, PokemonEntry], index if index is not None else build_pokemon_index(cast(list[dict[str, object]], pokemon_list)))

    # O(1) exact lookups
    try:
        num = int(q.lstrip("#"))
        if num in idx:
            return idx[num]
    except ValueError:
        pass

    if query.strip() in idx:
        return idx[query.strip()]

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
