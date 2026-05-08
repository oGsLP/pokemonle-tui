"""
数据加载与缓存 — 宝可梦基础数据 + PokeAPI 详细数据
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from constants import DATA_FILE, CACHE_DIR


def load_pokemon_data() -> List[Dict]:
    """加载宝可梦基础数据 (来自 pokemon_full_list.json)"""
    if not os.path.exists(DATA_FILE):
        print(f"错误: 宝可梦数据文件不存在: {DATA_FILE}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(DATA_FILE, "r", encoding="utf-8", errors="replace") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"错误: 宝可梦数据文件 JSON 格式无效: {DATA_FILE} ({exc})", file=sys.stderr)
        sys.exit(1)

    if not raw:
        print(f"警告: 宝可梦数据为空: {DATA_FILE}", file=sys.stderr)

    pokemon: List[Dict] = []
    for entry in raw:
        pokemon.append({
            "index": entry["index"],
            "id": int(entry["index"]),
            "name": entry["name"],
            "name_en": entry.get("name_en", ""),
            "name_jp": entry.get("name_jp", ""),
            "types": entry.get("types", []),
            "generation": entry.get("generation", ""),
        })
    return pokemon


def build_pokemon_index(pokemon_list: List[Dict]) -> Dict:
    """构建宝可梦快速索引，支持 id / 中文名 / 英文名 / 日文名 查找
    
    注意：地区形态可能与原版共享相同编号，因此 id 索引使用列表存储。
    名称索引仍然是一对一映射。
    """
    index: Dict = {}
    id_map: Dict[int, List[Dict]] = {}  # id -> [pokemon1, pokemon2, ...]
    
    for pokemon in pokemon_list:
        # 名称索引（精确匹配，一对一）
        index[pokemon["name"]] = pokemon

        normalized_en = pokemon["name_en"].lower().replace("-", "").replace(" ", "")
        if normalized_en:
            index[normalized_en] = pokemon

        normalized_jp = pokemon.get("name_jp", "").lower()
        if normalized_jp:
            index[normalized_jp] = pokemon
        
        # ID 索引（一对多，支持地区形态）
        poke_id = pokemon["id"]
        if poke_id not in id_map:
            id_map[poke_id] = []
        id_map[poke_id].append(pokemon)
    
    # 将 id_map 存入 index，使用特殊前缀避免冲突
    index["__id_map__"] = id_map

    return index


def fetch_pokeapi_data(poke_id: int) -> Optional[Dict]:
    """从 PokeAPI 获取详细数据，带本地文件缓存"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{poke_id:04d}.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    try:
        url = f"https://pokeapi.co/api/v2/pokemon/{poke_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "PokemonleCLI/1.0"})
        ssl_context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=8, context=ssl_context) as resp:
            data = json.loads(resp.read().decode())
        result = {
            "height": data["height"],
            "weight": data["weight"],
            "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
            "abilities": [a["ability"]["name"] for a in data["abilities"]],
        }
        with open(cache_file, "w") as f:
            json.dump(result, f)
        return result
    except urllib.error.URLError as exc:
        print(f"警告: 获取宝可梦 {poke_id} 的 PokeAPI 数据失败: {exc}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"警告: 处理宝可梦 {poke_id} 的 PokeAPI 数据失败: {exc}", file=sys.stderr)
        return None


def fetch_species_data(poke_id: int) -> Optional[Dict]:
    """从 PokeAPI 获取 species 数据，带本地文件缓存"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{poke_id:04d}_species.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    try:
        url = f"https://pokeapi.co/api/v2/pokemon-species/{poke_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "PokemonleCLI/1.0"})
        ssl_context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=8, context=ssl_context) as resp:
            data = json.loads(resp.read().decode())

        result = {
            "egg_groups": [group["name"] for group in data.get("egg_groups", [])],
            "capture_rate": data.get("capture_rate"),
            "hatch_counter": data.get("hatch_counter"),
            "gender_rate": data.get("gender_rate"),
            "is_legendary": data.get("is_legendary"),
            "is_mythical": data.get("is_mythical"),
            "growth_rate": data.get("growth_rate", {}).get("name"),
            "shape": data.get("shape", {}).get("name") if data.get("shape") else None,
            "habitat": data.get("habitat", {}).get("name") if data.get("habitat") else None,
        }

        with open(cache_file, "w") as f:
            json.dump(result, f)
        return result
    except urllib.error.URLError as exc:
        print(f"警告: 获取宝可梦 {poke_id} 的 species 数据失败: {exc}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"警告: 处理宝可梦 {poke_id} 的 species 数据失败: {exc}", file=sys.stderr)
        return None


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
