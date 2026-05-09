"""
数据加载与缓存 — 宝可梦基础数据 + PokeAPI 详细数据
"""
import json
import os
import ssl
import sys
import unicodedata
import urllib.error
import urllib.request
from typing import Callable, Dict, List, Optional

from constants import DATA_FILE, CACHE_DIR

# When True, suppress all progress prints (for threaded/background use)
QUIET = False


def load_pokemon_data() -> List[Dict]:
    """加载宝可梦基础数据 (来自 pokemon_full_list.json)"""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"宝可梦数据文件不存在: {DATA_FILE}")

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"宝可梦数据文件 JSON 格式无效: {DATA_FILE} ({exc})") from exc

    if not raw:
        print(f"警告: 宝可梦数据为空: {DATA_FILE}", file=sys.stderr)

    pokemon: List[Dict] = []
    for entry in raw:
        try:
            name_en = entry.get("name_en", "")
            pokemon.append({
                "index": entry["index"],
                "id": int(entry["index"]),
                "name": entry["name"],
                "name_en": name_en,
                "name_jp": entry.get("name_jp", ""),
                "types": entry.get("types", []),
                "generation": entry.get("generation", ""),
                "_name_en_norm": name_en.lower().replace("-", "").replace(" ", ""),
                "_name_jp_norm": unicodedata.normalize("NFKC", entry.get("name_jp", "")).lower(),
                "_id_str": str(int(entry["index"])),
            })
        except (KeyError, ValueError) as exc:
            print(f"警告: 跳过损坏的宝可梦数据条目: {exc}", file=sys.stderr)
            continue
    return pokemon


def build_pokemon_index(pokemon_list: List[Dict]) -> Dict:
    """构建宝可梦快速索引，支持 id / 中文名 / 英文名 / 日文名 查找"""
    index: Dict = {}
    for pokemon in pokemon_list:
        # ID → first entry wins (original forms appear before regional variants)
        index.setdefault(pokemon["id"], pokemon)
        index[pokemon["name"]] = pokemon

        normalized_en = pokemon["name_en"].lower().replace("-", "").replace(" ", "")
        if normalized_en:
            index[normalized_en] = pokemon

        normalized_jp = pokemon.get("name_jp", "").lower()
        if normalized_jp:
            index[normalized_jp] = pokemon

    return index


def _cached_or_fetch(
    cache_file: str, url: str, extract: Callable[[dict], dict], label: str
) -> Optional[Dict]:
    """通用缓存+拉取逻辑：读缓存 → 网络拉取 → 原子写缓存"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            if not QUIET:
                print(f"警告: 缓存文件损坏，跳过: {cache_file}", file=sys.stderr)
            return None

    if not QUIET:
        print(f"  ⏳ 正在从 PokeAPI 获取 {label}...", file=sys.stderr)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PokemonleCLI/1.0"})
        ssl_context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=8, context=ssl_context) as resp:
            if resp.status != 200:
                if not QUIET:
                    print(f"  ⚠ PokeAPI 返回状态码 {resp.status} ({label})", file=sys.stderr)
                return None
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        if not QUIET:
            print(f"  ⚠ 获取 {label} 失败: {exc}", file=sys.stderr)
        return None
    except Exception as exc:
        if not QUIET:
            print(f"  ⚠ 处理 {label} 失败: {exc}", file=sys.stderr)
        return None

    result = extract(data)
    tmp_file = cache_file + ".tmp"
    try:
        with open(tmp_file, "w") as f:
            json.dump(result, f)
        os.replace(tmp_file, cache_file)
    except OSError as exc:
        if not QUIET:
            print(f"警告: 无法写入缓存文件 {cache_file}: {exc}", file=sys.stderr)
    if not QUIET:
        print(f"  ✅ {label} 已缓存", file=sys.stderr)
    return result


def fetch_pokeapi_data(poke_id: int) -> Optional[Dict]:
    """从 PokeAPI 获取详细数据，带本地文件缓存"""
    cache_file = os.path.join(CACHE_DIR, f"{poke_id:04d}.json")
    url = f"https://pokeapi.co/api/v2/pokemon/{poke_id}"

    def _extract(data: dict) -> dict:
        return {
            "height": data["height"],
            "weight": data["weight"],
            "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
            "abilities": [a["ability"]["name"] for a in data["abilities"]],
        }

    return _cached_or_fetch(cache_file, url, _extract, f"宝可梦 #{poke_id}")


def fetch_species_data(poke_id: int) -> Optional[Dict]:
    """从 PokeAPI 获取 species 数据，带本地文件缓存"""
    cache_file = os.path.join(CACHE_DIR, f"{poke_id:04d}_species.json")
    url = f"https://pokeapi.co/api/v2/pokemon-species/{poke_id}"

    def _extract(data: dict) -> dict:
        return {
            "egg_groups": [group["name"] for group in data.get("egg_groups", [])],
            "capture_rate": data.get("capture_rate"),
        }

    return _cached_or_fetch(cache_file, url, _extract, f"species #{poke_id}")


def get_pokemon_details(poke: Dict) -> Dict:
    """获取宝可梦详细信息（基础数据 + PokeAPI 补充种族值/身高/体重）"""
    details: Dict = {**poke}
    api_data = fetch_pokeapi_data(poke["id"])
    if api_data:
        details.update(api_data)
        stats = api_data["stats"]
        details["stat_total"] = sum(stats.values())
        details["speed"] = stats.get("speed", 0)
        details["hp"] = stats.get("hp", 0)
        details["attack"] = stats.get("attack", 0)
        details["defense"] = stats.get("defense", 0)
        details["sp_attack"] = stats.get("special-attack", 0)
        details["sp_defense"] = stats.get("special-defense", 0)
    return details
