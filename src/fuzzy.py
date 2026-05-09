"""
模糊匹配与补全 — 宝可梦查找 + prompt_toolkit 补全器
"""
from __future__ import annotations

from collections import deque

from typing import Any, override

from .constants import GEN_MAP, TYPE_COLORS, TYPE_CN_TO_EN_MAP
from .data import build_pokemon_index
from .poketypes import PokemonEntry


class _TrieNode:
    __slots__ = ("children", "pokemon_ids")

    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.pokemon_ids: list[int] = []


class PokemonTrie:
    """Prefix trie for fast Pokémon name autocomplete.

    Indexes Chinese, English (normalized), Japanese names, and IDs
    for O(m) prefix lookup instead of O(n) full-scan.
    """

    def __init__(self, pokemon_list: list[PokemonEntry]) -> None:
        self._root = _TrieNode()
        self._pokemon_by_id: dict[int, PokemonEntry] = {}
        self._build(pokemon_list)

    def _insert(self, text: str, poke_id: int) -> None:
        if not text:
            return
        node = self._root
        for ch in text:
            if ch not in node.children:
                node.children[ch] = _TrieNode()
            node = node.children[ch]
        if poke_id not in node.pokemon_ids:
            node.pokemon_ids.append(poke_id)

    def _build(self, pokemon_list: list[PokemonEntry]) -> None:
        for p in pokemon_list:
            pid = p["id"]
            self._pokemon_by_id[pid] = p
            self._insert(p["name"], pid)
            en = p.get("_name_en_norm", p["name_en"].lower().replace("-", "").replace(" ", ""))
            if en:
                self._insert(en, pid)
            jp = p.get("_name_jp_norm", p.get("name_jp", "").lower())
            if jp:
                self._insert(jp, pid)
            self._insert(p.get("_id_str", str(pid)), pid)

    def prefix_search(self, prefix: str, limit: int = 15) -> list[PokemonEntry]:
        prefix = prefix.lower().strip()
        if not prefix:
            return []
        node = self._root
        for ch in prefix:
            if ch not in node.children:
                return []
            node = node.children[ch]
        ids = self._collect_ids(node, limit)
        return [self._pokemon_by_id[pid] for pid in ids if pid in self._pokemon_by_id]

    def _collect_ids(self, node: _TrieNode, limit: int) -> list[int]:
        result: list[int] = []
        queue: deque[_TrieNode] = deque([node])
        while queue and len(result) < limit:
            cur = queue.popleft()
            for pid in cur.pokemon_ids:
                if pid not in result:
                    result.append(pid)
                    if len(result) >= limit:
                        return result
            for child in cur.children.values():
                queue.append(child)
        return result


def score_pokemon(query: str, p: PokemonEntry) -> int:
    """给宝可梦打分：query 与 name 的匹配程度，分数越高越相关"""
    q = query.lower().strip()
    name_en_norm: str = p.get("_name_en_norm", p["name_en"].lower().replace("-", "").replace(" ", ""))
    name_cn = p["name"]
    name_jp_norm: str = p.get("_name_jp_norm", p.get("name_jp", "").lower())
    poke_id = p.get("_id_str", str(p["id"]))

    # 编号精确匹配
    q_stripped = q.lstrip("#")
    try:
        q_num = int(q_stripped)
        if q_num == p["id"]:
            return 100
    except ValueError:
        pass
    q_num_digits = q_stripped
    if q_num_digits.isdigit() and len(q_num_digits) >= 2:
        try:
            if str(p["id"]).startswith(q_num_digits):
                return 90
        except (ValueError, KeyError):
            pass
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


def get_fuzzy_matches(query: str, pokemon_list: list[PokemonEntry], limit: int = 15, *, trie: PokemonTrie | None = None) -> list[PokemonEntry]:
    """返回按匹配度排序的模糊匹配结果。

    If trie provided, use fast prefix search first; fall back to
    full-scan scoring only when trie returns no results.
    """
    q = query.strip()
    if not q:
        return []

    if trie is not None:
        trie_results = trie.prefix_search(q, limit)
        if trie_results:
            return trie_results[:limit]

    scored = []
    for p in pokemon_list:
        s = score_pokemon(q, p)
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]


def find_pokemon(query: str, pokemon_list: list[PokemonEntry], index: dict[int | str, PokemonEntry] | None = None) -> PokemonEntry | None:
    """精确查找宝可梦（中英文名、编号），找不到则取最佳模糊匹配"""
    q = query.strip().lower()
    idx = index if index is not None else build_pokemon_index(pokemon_list)

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
    from prompt_toolkit.formatted_text import FormattedText
    _HAS_PROMPT_TOOLKIT = True
except ImportError:
    _HAS_PROMPT_TOOLKIT = False


if _HAS_PROMPT_TOOLKIT:

    class PokemonCompleter(Completer):
        """prompt_toolkit 模糊补全器 — 输入时弹出候选列表"""

        def __init__(self, pokemon_list: list[PokemonEntry]) -> None:
            self.pokemon_list = pokemon_list
            self._trie = PokemonTrie(pokemon_list)

        @override
        def get_completions(self, document: Any, complete_event: Any):
            text = document.text_before_cursor
            words = text.rstrip().split()
            if not words:
                return
            query = words[-1] if text and not text.endswith(" ") else ""
            if not query:
                return

            matches = get_fuzzy_matches(query, self.pokemon_list, limit=15, trie=self._trie)
            for p in matches:
                types_str = "/".join(p["types"])
                primary_type = p["types"][0] if p.get("types") else ""
                type_key = TYPE_CN_TO_EN_MAP.get(primary_type, "")
                type_color = TYPE_COLORS.get(type_key, "")
                gen_str = GEN_MAP.get(p["generation"], (p["generation"],))[0]
                display_text = f"{p['name']} ({p['name_en']}) #{p['id']:04d}"
                if type_color:
                    meta = FormattedText([
                        ("bold", "["),
                        (f"fg:{type_color}", types_str),
                        ("bold", f"] · {gen_str}"),
                    ])
                else:
                    meta = FormattedText([
                        ("", f"[{types_str}] · {gen_str}"),
                    ])
                yield Completion(
                    text=p["name"],
                    start_position=-len(query),
                    display=display_text,
                    display_meta=meta,
                )

else:
    PokemonCompleter = None  # type: ignore[assignment]
