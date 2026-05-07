"""
单元测试 — constants / data / config / comparison / fuzzy / stats
运行: cd /home/ogslp/Projects/Opencode/pokemonle-tui && python3 -m pytest tests/ -v
"""
# pyright: reportMissingImports=false, reportUnusedImport=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
import os
import sys
import pytest

# 确保 src/ 在 path 里 (必须在 import src 之前)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 统一导入 — 所有模块内部也是 import constants，保持引用一致
import constants
from constants import (
    PROJECT_DIR, DATA_FILE, CACHE_DIR,
    Hint, TYPE_COLORS, GEN_MAP, ALL_GENERATIONS, GAME_MODE_PRESETS, DEFAULT_CONFIG,
)
from data import load_pokemon_data, build_pokemon_index, fetch_pokeapi_data, fetch_species_data, get_pokemon_details
from config import load_config, save_config
from comparison import compare_pokemon
from fuzzy import score_pokemon, get_fuzzy_matches, find_pokemon
from stats import save_game_stats, get_stats_summary, _load_stats


# ══════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════

@pytest.fixture(scope="session")
def pokemon_list():
    """加载完整宝可梦数据（整个测试会话共享）"""
    return load_pokemon_data()


@pytest.fixture
def pokemon_25(pokemon_list):
    """皮卡丘"""
    return next(p for p in pokemon_list if p["id"] == 25)


@pytest.fixture
def pokemon_1(pokemon_list):
    """妙蛙种子"""
    return next(p for p in pokemon_list if p["id"] == 1)


@pytest.fixture
def pokemon_4(pokemon_list):
    """小火龙"""
    return next(p for p in pokemon_list if p["id"] == 4)


@pytest.fixture
def default_config():
    return dict(DEFAULT_CONFIG)


# ══════════════════════════════════════════════
#  Test: constants.py
# ══════════════════════════════════════════════

class TestConstants:
    def test_project_dir_exists(self):
        assert os.path.isdir(PROJECT_DIR)

    def test_data_file_exists(self):
        assert os.path.isfile(DATA_FILE), f"{DATA_FILE} 不存在"

    def test_all_generations_count(self):
        assert len(ALL_GENERATIONS) == 9

    def test_gen_map_covers_all_generations(self):
        for g in ALL_GENERATIONS:
            assert g in GEN_MAP
            short, num = GEN_MAP[g]
            assert isinstance(short, str)
            assert isinstance(num, int)

    def test_type_colors_has_18_types(self):
        assert len(TYPE_COLORS) == 18

    def test_hint_namedtuple(self):
        h = Hint("编号", "#0025", "exact")
        assert h.label == "编号"
        assert h.value == "#0025"
        assert h.level == "exact"
        assert h.arrow is None

    def test_hint_namedtuple_with_arrow(self):
        h = Hint("编号", "#0025", "close", "↑")
        assert h.arrow == "↑"

    def test_hint_indexed_access(self):
        h = Hint("编号", "#0025", "exact")
        assert h[0] == "编号"
        assert h[2] == "exact"

    def test_game_mode_presets_exists(self):
        assert len(GAME_MODE_PRESETS) == 3
        for key in ("easy", "normal", "hard"):
            assert key in GAME_MODE_PRESETS

    def test_game_mode_presets_structure(self):
        expected_keys = {
            "id_range", "stat_range", "speed_range", "detail_range",
            "height_range", "weight_range", "default_guesses",
        }
        for preset in GAME_MODE_PRESETS.values():
            assert expected_keys == set(preset.keys())

    def test_normal_preset_values(self):
        normal = GAME_MODE_PRESETS["normal"]
        assert normal["id_range"] == 10
        assert normal["stat_range"] == 30
        assert normal["speed_range"] == 15
        assert normal["detail_range"] == 10
        assert normal["height_range"] == 5
        assert normal["weight_range"] == 30
        assert normal["default_guesses"] == 10

    def test_default_config_keys(self):
        expected = {"game_mode", "generations", "max_guesses", "show_more_stats",
                    "show_more_appearance", "show_egg_group", "show_gen_arrow",
                    "reverse_order", "mischief"}
        assert expected == set(DEFAULT_CONFIG.keys())

    def test_default_config_all_generations(self):
        assert len(DEFAULT_CONFIG["generations"]) == 9


# ══════════════════════════════════════════════
#  Test: data.py
# ══════════════════════════════════════════════

class TestData:
    def test_load_pokemon_data_count(self, pokemon_list):
        assert len(pokemon_list) > 1000

    def test_pokemon_entry_fields(self, pokemon_25):
        assert pokemon_25["id"] == 25
        assert pokemon_25["name"] == "皮卡丘"
        assert pokemon_25["name_en"] == "Pikachu"
        assert isinstance(pokemon_25["types"], list)
        assert len(pokemon_25["types"]) >= 1
        assert pokemon_25["generation"] in ALL_GENERATIONS

    def test_pokemon_id_consistency(self, pokemon_list):
        for p in pokemon_list:
            assert p["id"] == int(p["index"])

    def test_fetch_pokeapi_cache_hit(self):
        """已缓存的 PokeAPI 数据可以直接读取"""
        cached_ids = []
        if os.path.isdir(CACHE_DIR):
            cached_ids = [int(f[:4]) for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
        if not cached_ids:
            pytest.skip("没有 PokeAPI 缓存数据")
        data = fetch_pokeapi_data(cached_ids[0])
        assert data is not None
        assert "height" in data
        assert "weight" in data
        assert "stats" in data
        assert isinstance(data["stats"], dict)

    def test_fetch_pokeapi_invalid_id(self):
        """不存在的 ID 应返回 None"""
        result = fetch_pokeapi_data(999999)
        assert result is None

    def test_build_pokemon_index_lookups(self, pokemon_list):
        idx = build_pokemon_index(pokemon_list)
        assert idx[25]["name"] == "皮卡丘"
        assert idx["皮卡丘"]["id"] == 25
        assert idx["pikachu"]["id"] == 25

    def test_fetch_species_data_cached(self):
        species_cache_ids = []
        if os.path.isdir(CACHE_DIR):
            species_cache_ids = [
                int(f[:4])
                for f in os.listdir(CACHE_DIR)
                if f.endswith("_species.json")
            ]
        if not species_cache_ids:
            pytest.skip("没有 species 缓存数据")
        data = fetch_species_data(species_cache_ids[0])
        assert data is not None
        assert "egg_groups" in data
        assert isinstance(data["egg_groups"], list)

    def test_get_pokemon_details_fields(self, pokemon_1):
        details = get_pokemon_details(pokemon_1)
        assert details["id"] == 1
        assert "types" in details
        assert "generation" in details
        if "stat_total" in details:
            assert isinstance(details["stat_total"], int)
            assert details["stat_total"] > 0


# ══════════════════════════════════════════════
#  Test: config.py
# ══════════════════════════════════════════════

class TestConfig:
    def test_load_config_returns_dict(self):
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_load_config_has_all_keys(self):
        cfg = load_config()
        for key in DEFAULT_CONFIG:
            assert key in cfg, f"配置缺少字段: {key}"

    def test_save_and_load_config(self, tmp_path):
        """保存后重新加载应保持一致"""
        old = constants.CONFIG_FILE
        try:
            constants.CONFIG_FILE = str(tmp_path / "test_config.json")
            test_cfg = {"game_mode": "hard", "max_guesses": 15, "generations": ["第一世代"]}
            save_config(test_cfg)
            loaded = load_config()
            assert loaded["game_mode"] == "hard"
            assert loaded["max_guesses"] == 15
        finally:
            constants.CONFIG_FILE = old


# ══════════════════════════════════════════════
#  Test: comparison.py
# ══════════════════════════════════════════════

class TestComparison:
    def test_same_pokemon_all_exact(self, pokemon_25, default_config):
        """相同宝可梦应该全部 exact（属性除外，属性只有 partial/miss）"""
        details = get_pokemon_details(pokemon_25)
        hints = compare_pokemon(details, details, default_config)
        for h in hints:
            level = h[2]
            if h[0] == "属性":
                assert level == "partial", f"属性应该是 partial，实际是 {level}"
            else:
                assert level == "exact", f"{h[0]} 应该是 exact，实际是 {level}"

    def test_different_pokemon_has_non_exact(self, pokemon_1, pokemon_4, default_config):
        """不同宝可梦应该有非 exact 的提示"""
        t = get_pokemon_details(pokemon_1)
        g = get_pokemon_details(pokemon_4)
        hints = compare_pokemon(t, g, default_config)
        levels = [h[2] for h in hints]
        assert any(lv != "exact" for lv in levels)

    def test_hint_labels_present(self, pokemon_1, pokemon_4, default_config):
        """所有基础提示标签都应该存在"""
        t = get_pokemon_details(pokemon_1)
        g = get_pokemon_details(pokemon_4)
        hints = compare_pokemon(t, g, default_config)
        labels = [h[0] for h in hints]
        for expected in ["编号", "属性", "世代"]:
            assert expected in labels, f"缺少提示: {expected}"

        t_egg = t.get("egg_groups")
        g_egg = g.get("egg_groups")
        config_with_egg = {**default_config, "show_egg_group": True}
        egg_hints = compare_pokemon(t, g, config_with_egg)
        egg_labels = [h[0] for h in egg_hints]
        if isinstance(t_egg, list) and isinstance(g_egg, list) and t_egg and g_egg:
            assert "蛋组" in egg_labels, "缺少提示: 蛋组"

    def test_gen_arrow_disabled(self, pokemon_1, pokemon_4):
        """世代箭头关闭时不应该有第4个元素(箭头)"""
        t = get_pokemon_details(pokemon_1)
        g = get_pokemon_details(pokemon_4)
        config_no_arrow = {**DEFAULT_CONFIG, "show_gen_arrow": False}
        hints = compare_pokemon(t, g, config_no_arrow)
        gen_hint = next(h for h in hints if h[0] == "世代")
        if gen_hint[2] != "exact":
            assert len(gen_hint) == 3, f"世代提示不应该有箭头: {gen_hint}"

    def test_show_more_stats(self, pokemon_1, pokemon_4):
        """开启更多种族值后应该有 HP/攻击/防御等"""
        t = get_pokemon_details(pokemon_1)
        g = get_pokemon_details(pokemon_4)
        config_more = {**DEFAULT_CONFIG, "show_more_stats": True}
        hints = compare_pokemon(t, g, config_more)
        labels = [h[0] for h in hints]
        if "stat_total" in t and "stat_total" in g:
            for expected in ["HP", "攻击", "防御", "特攻", "特防"]:
                assert expected in labels, f"缺少更多种族值提示: {expected}"

    def test_arrow_direction(self, pokemon_1, pokemon_25, default_config):
        """编号 25 比 1 大，应该有 ↑ 箭头（目标比猜测大）"""
        t = get_pokemon_details(pokemon_25)  # 目标: 25
        g = get_pokemon_details(pokemon_1)   # 猜测: 1
        hints = compare_pokemon(t, g, default_config)
        id_hint = next(h for h in hints if h[0] == "编号")
        if len(id_hint) == 4:
            assert id_hint[3] == "↑"

    def test_hint_tuple_lengths(self, pokemon_1, pokemon_25, default_config):
        """每个提示要么3个要么4个元素"""
        t = get_pokemon_details(pokemon_1)
        g = get_pokemon_details(pokemon_25)
        hints = compare_pokemon(t, g, default_config)
        for h in hints:
            assert len(h) in (3, 4), f"提示格式错误: {h}"

    def test_mode_affects_thresholds(self):
        target = {
            "id": 25,
            "types": ["电"],
            "generation": "第一世代",
            "stat_total": 300,
            "speed": 100,
        }
        guess = {
            "id": 45,
            "types": ["电"],
            "generation": "第一世代",
            "stat_total": 300,
            "speed": 100,
        }

        easy_hints = compare_pokemon(target, guess, {**DEFAULT_CONFIG, "game_mode": "easy"})
        hard_hints = compare_pokemon(target, guess, {**DEFAULT_CONFIG, "game_mode": "hard"})

        easy_id_hint = next(h for h in easy_hints if h.label == "编号")
        hard_id_hint = next(h for h in hard_hints if h.label == "编号")
        assert easy_id_hint.level == "close"
        assert hard_id_hint.level == "far"

    def test_egg_group_hints(self):
        target = {
            "id": 1,
            "types": ["草", "毒"],
            "generation": "第一世代",
            "egg_groups": ["monster", "grass"],
        }
        guess = {
            "id": 2,
            "types": ["草", "毒"],
            "generation": "第一世代",
            "egg_groups": ["monster", "grass"],
        }

        hints = compare_pokemon(target, guess, {**DEFAULT_CONFIG, "show_egg_group": True})
        egg_hint = next((h for h in hints if h.label == "蛋组"), None)
        assert egg_hint is not None
        assert egg_hint.level == "exact"
        assert egg_hint.value == "monster/grass"

    def test_type_partial_match_only_matching_bolded(self):
        """Target 草/龙, Guess 草/飞行 → only 草 in matched set"""
        target = {"id": 103, "types": ["草", "龙"], "generation": "第一世代"}
        guess = {"id": 357, "types": ["草", "飞行"], "generation": "第三世代"}
        hints = compare_pokemon(target, guess, DEFAULT_CONFIG)
        type_hint = next(h for h in hints if h.label == "属性")
        matched = set(type_hint.arrow.split("/")) if type_hint.arrow else set()
        assert "草" in matched
        assert "飞行" not in matched
        assert type_hint.value == "草/飞行"

    def test_type_no_match_all_dimmed(self):
        """Target 草/龙, Guess 水/火 → no match"""
        target = {"id": 103, "types": ["草", "龙"], "generation": "第一世代"}
        guess = {"id": 6, "types": ["水", "火"], "generation": "第一世代"}
        hints = compare_pokemon(target, guess, DEFAULT_CONFIG)
        type_hint = next(h for h in hints if h.label == "属性")
        assert type_hint.level == "miss"
        assert type_hint.value == "水/火"
        assert type_hint.arrow is None

    def test_type_single_vs_dual(self):
        """Target 单属性(地面), Guess 双属性(地面/超能力) → only 地面 matched"""
        target = {"id": 27, "types": ["地面"], "generation": "第一世代"}
        guess = {"id": 122, "types": ["地面", "超能力"], "generation": "第二世代"}
        hints = compare_pokemon(target, guess, DEFAULT_CONFIG)
        type_hint = next(h for h in hints if h.label == "属性")
        matched = set(type_hint.arrow.split("/")) if type_hint.arrow else set()
        assert "地面" in matched
        assert "超能力" not in matched

    def test_type_both_match(self):
        """Target 草/龙, Guess 草/龙 → both matched"""
        target = {"id": 103, "types": ["草", "龙"], "generation": "第一世代"}
        guess = {"id": 887, "types": ["草", "龙"], "generation": "第八世代"}
        hints = compare_pokemon(target, guess, DEFAULT_CONFIG)
        type_hint = next(h for h in hints if h.label == "属性")
        matched = set(type_hint.arrow.split("/")) if type_hint.arrow else set()
        assert "草" in matched
        assert "龙" in matched


# ══════════════════════════════════════════════
#  Test: fuzzy.py
# ══════════════════════════════════════════════

class TestFuzzy:
    def test_build_pokemon_index(self, pokemon_list):
        idx = build_pokemon_index(pokemon_list)
        assert isinstance(idx, dict)
        assert idx[25]["name"] == "皮卡丘"

    def test_exact_chinese_name(self, pokemon_25):
        assert score_pokemon("皮卡丘", pokemon_25) == 100

    def test_exact_english_name(self, pokemon_25):
        assert score_pokemon("pikachu", pokemon_25) == 100

    def test_exact_id(self, pokemon_25):
        assert score_pokemon("25", pokemon_25) == 100

    def test_exact_id_with_hash(self, pokemon_25):
        assert score_pokemon("#25", pokemon_25) == 100

    def test_chinese_prefix(self, pokemon_25):
        assert score_pokemon("皮卡", pokemon_25) == 85

    def test_english_prefix(self, pokemon_25):
        score = score_pokemon("pika", pokemon_25)
        assert score >= 78

    def test_chinese_contains(self, pokemon_25):
        assert score_pokemon("卡丘", pokemon_25) == 70

    def test_no_match(self, pokemon_25):
        assert score_pokemon("xyz999", pokemon_25) == 0

    def test_empty_query(self, pokemon_list):
        assert get_fuzzy_matches("", pokemon_list) == []
        assert get_fuzzy_matches("  ", pokemon_list) == []

    def test_fuzzy_matches_sorted_by_score(self, pokemon_list):
        matches = get_fuzzy_matches("皮", pokemon_list, limit=10)
        assert len(matches) > 0
        assert matches[0]["name"] == "皮卡丘"

    def test_fuzzy_matches_limit(self, pokemon_list):
        matches = get_fuzzy_matches("龙", pokemon_list, limit=3)
        assert len(matches) <= 3

    def test_find_pokemon_exact_cn(self, pokemon_list):
        result = find_pokemon("皮卡丘", pokemon_list)
        assert result["id"] == 25

    def test_find_pokemon_exact_en(self, pokemon_list):
        result = find_pokemon("pikachu", pokemon_list)
        assert result["id"] == 25

    def test_find_pokemon_exact_id(self, pokemon_list):
        result = find_pokemon("#25", pokemon_list)
        assert result["id"] == 25

    def test_find_pokemon_fallback(self, pokemon_list):
        result = find_pokemon("皮卡", pokemon_list)
        assert result is not None
        assert result["id"] == 25

    def test_find_pokemon_not_found(self, pokemon_list):
        result = find_pokemon("zzzzz_not_pokemon", pokemon_list)
        assert result is None


# ══════════════════════════════════════════════
#  Test: stats.py
# ══════════════════════════════════════════════

class TestStats:
    def test_save_and_load_stats(self, tmp_path):
        """保存后重新加载应包含新记录"""
        old = constants.STATS_FILE
        try:
            constants.STATS_FILE = str(tmp_path / "test_stats.json")
            save_game_stats(True, 3)
            stats = _load_stats()
            assert stats["total"] == 1
            assert stats["wins"] == 1
            assert stats["guesses_history"] == [3]
        finally:
            constants.STATS_FILE = old

    def test_save_loss(self, tmp_path):
        old = constants.STATS_FILE
        try:
            constants.STATS_FILE = str(tmp_path / "test_stats.json")
            save_game_stats(False, 10)
            stats = _load_stats()
            assert stats["total"] == 1
            assert stats["wins"] == 0
        finally:
            constants.STATS_FILE = old

    def test_multiple_games(self, tmp_path):
        old = constants.STATS_FILE
        try:
            constants.STATS_FILE = str(tmp_path / "test_stats.json")
            save_game_stats(True, 3)
            save_game_stats(True, 5)
            save_game_stats(False, 10)
            stats = _load_stats()
            assert stats["total"] == 3
            assert stats["wins"] == 2
            assert stats["guesses_history"] == [3, 5, 10]
        finally:
            constants.STATS_FILE = old

    def test_get_stats_summary_format(self):
        summary = get_stats_summary(1082)
        assert "宝可梦池" in summary
        assert "1082" in summary
        assert "胜率" in summary
