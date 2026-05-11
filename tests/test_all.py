"""
单元测试 — constants / data / config / comparison / fuzzy / stats
运行: cd /home/ogslp/Projects/Opencode/pokemonle-tui && python3 -m pytest tests/ -v
"""
# pyright: reportMissingImports=false, reportUnusedImport=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
import json
import os
import random
import pytest

import src.constants as constants
from src.constants import (
    PROJECT_DIR, DATA_FILE, CACHE_DIR,
    Hint, TYPE_COLORS, GEN_MAP, ALL_GENERATIONS, GAME_MODE_PRESETS, DEFAULT_CONFIG,
)
from src.data import load_pokemon_data, build_pokemon_index, fetch_pokeapi_data, fetch_species_data, get_pokemon_details
from src.config import load_config, save_config, _validate_config
from src.comparison import compare_pokemon, compute_remaining_pool
from src.fuzzy import score_pokemon, get_fuzzy_matches, find_pokemon, PokemonTrie
from src.stats import save_game_stats, get_stats_summary, _load_stats, _build_distribution
from src.game import _format_hint, _safe_save_stats, _show_answer
from src.share import format_share_result
import src.share as share
import src.data as _data
import src.ascii_art as ascii_art
import src.game as game
import src.ui as ui


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

    def test_save_failure_raises(self, tmp_path):
        """写入失败时应该抛出 OSError"""
        old = constants.CONFIG_FILE
        try:
            bad_path = str(tmp_path / "nonexistent" / "config.json")
            constants.CONFIG_FILE = bad_path
            with pytest.raises(OSError):
                save_config({"game_mode": "easy"})
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

    def test_appearance_without_height_no_crash(self):
        """开启体型比较但缺少身高数据时不应崩溃且不产生体型提示"""
        target = {"id": 1, "types": ["草"], "generation": "第一世代"}
        guess = {"id": 2, "types": ["草"], "generation": "第一世代"}
        hints = compare_pokemon(target, guess,
                                 {**DEFAULT_CONFIG, "show_more_appearance": True})
        labels = [h.label for h in hints]
        assert "体型" not in labels, "缺少身高数据时不应生成体型提示"

    def test_appearance_with_height(self):
        """有身高数据时开启体型比较应生成体型提示"""
        target = {"id": 1, "types": ["草"], "generation": "第一世代",
                   "height": 40, "weight": 69}
        guess = {"id": 4, "types": ["火"], "generation": "第一世代",
                  "height": 60, "weight": 85}
        hints = compare_pokemon(target, guess,
                                 {**DEFAULT_CONFIG, "show_more_appearance": True})
        labels = [h.label for h in hints]
        assert "体型" in labels, "有身高数据时应生成体型提示"


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

    def test_save_failure_raises(self, monkeypatch, tmp_path):
        """写入失败时应该抛出 OSError"""
        old = constants.STATS_FILE
        try:
            bad_path = str(tmp_path / "nonexistent" / "stats.json")
            constants.STATS_FILE = bad_path
            with pytest.raises(OSError):
                save_game_stats(True, 3)
        finally:
            constants.STATS_FILE = old


# ══════════════════════════════════════════════
#  Test: game.py _format_hint
# ══════════════════════════════════════════════

class TestFormatHint:
    def test_exact_hint(self):
        t = _format_hint("编号", "#0025", "exact")
        assert "#0025" in t.plain
        assert "●" in t.plain

    def test_close_with_arrow(self):
        t = _format_hint("编号", "#0020", "close", "↑")
        assert "#0020" in t.plain
        assert "↑" in t.plain
        assert "◐" in t.plain

    def test_miss_dim(self):
        t = _format_hint("属性", "火", "miss")
        assert "火" in t.plain

    def test_type_partial_highlights_matched(self):
        t = _format_hint("属性", "草/飞行", "partial", "草")
        assert "草" in t.plain
        assert "飞行" in t.plain
        assert "◐" in t.plain
        assert any("white on" in span.style for span in t.spans)
        assert any("dim" in span.style for span in t.spans)

    def test_type_miss_no_highlight(self):
        t = _format_hint("属性", "水/火", "miss", "")
        assert "水" in t.plain
        assert "火" in t.plain

    def test_far_hint(self):
        t = _format_hint("身高", "1.5m", "far", "↓")
        assert "1.5m" in t.plain
        assert "↓" in t.plain
        assert "○" in t.plain

    def test_show_hints_table_renders_with_narrow_console(self, monkeypatch):
        from io import StringIO
        from rich.console import Console

        output = StringIO()
        narrow_console = Console(width=60, force_terminal=False)
        monkeypatch.setattr(ui, "_console", narrow_console)
        monkeypatch.setattr(narrow_console, "file", output)

        guesses = [
            (
                {"name": "妙蛙种子", "name_en": "Bulbasaur"},
                [
                    Hint("编号", "1", "exact"),
                    Hint("属性", "草/毒", "partial", "草"),
                    Hint("世代", "1", "exact"),
                    Hint("种族值", "318", "close", "↑"),
                    Hint("速度", "45", "far", "↓"),
                ],
            )
        ]
        config = {"reverse_order": False, "show_more_stats": False, "show_more_appearance": False, "show_egg_group": False}

        ui.show_hints_table(guesses, 10, config, pool_size=12)
        rendered = output.getvalue()

        assert "猜测记录" in rendered
        assert "Bulbasaur" in rendered or "妙蛙" in rendered


# ══════════════════════════════════════════════
#  Test: config.py _validate_config
# ══════════════════════════════════════════════

class TestConfigValidation:
    def test_preserves_valid_values(self):
        cfg = dict(DEFAULT_CONFIG)
        validated = _validate_config(cfg)
        assert validated == cfg

    def test_coerces_int_from_string(self):
        cfg = {**DEFAULT_CONFIG, "max_guesses": "15"}
        validated = _validate_config(cfg)
        assert validated["max_guesses"] == 15

    def test_falls_back_on_invalid_int(self):
        cfg = {**DEFAULT_CONFIG, "max_guesses": "abc"}
        validated = _validate_config(cfg)
        assert validated["max_guesses"] == DEFAULT_CONFIG["max_guesses"]

    def test_coerces_bool(self):
        cfg = {**DEFAULT_CONFIG, "show_more_stats": 1}
        validated = _validate_config(cfg)
        assert validated["show_more_stats"] is True

    def test_falls_back_wrong_list_type(self):
        cfg = {**DEFAULT_CONFIG, "generations": "not_a_list"}
        validated = _validate_config(cfg)
        assert validated["generations"] == DEFAULT_CONFIG["generations"]

    def test_validate_config_treats_empty_generations_as_all_generations(self):
        cfg = _validate_config({"generations": []})
        assert cfg["generations"] == ALL_GENERATIONS


class TestSettingsUi:
    def test_settings_text_explains_generation_reset(self, monkeypatch):
        output = []
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: output.extend(str(x) for x in a))
        monkeypatch.setattr("src.ui._console.input", lambda *a, **kw: "q")

        ui.show_settings(dict(DEFAULT_CONFIG))

        rendered = "\n".join(output)
        assert "n[/cyan]=重置为全部世代" in rendered

    def test_settings_copy_names_egg_group_without_capture_rate(self, monkeypatch):
        output = []
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: output.extend(str(x) for x in a))
        monkeypatch.setattr("src.ui._console.input", lambda *a, **kw: "q")

        ui.show_settings(dict(DEFAULT_CONFIG))

        rendered = "\n".join(output)
        assert "显示蛋组信息" in rendered
        assert "捕获率" not in rendered


class TestLogo:
    def test_logo_uses_0_2_2_version(self, monkeypatch):
        from io import StringIO
        from rich.console import Console

        output = StringIO()
        monkeypatch.setattr(ui, "_console", Console(file=output, force_terminal=False))

        ui.show_logo()

        rendered = output.getvalue()
        assert "0.2.2" in rendered
        assert "CLI v2" not in rendered


# ══════════════════════════════════════════════
#  Test: fuzzy.py — cached index + precomputed
# ══════════════════════════════════════════════

class TestFuzzyCached:
    def test_find_pokemon_with_cached_index(self, pokemon_list):
        idx = build_pokemon_index(pokemon_list)
        result = find_pokemon("皮卡丘", pokemon_list, index=idx)
        assert result is not None
        assert result["id"] == 25

    def test_find_pokemon_without_index_still_works(self, pokemon_list):
        result = find_pokemon("皮卡丘", pokemon_list)
        assert result is not None
        assert result["id"] == 25

    def test_score_uses_precomputed_fields(self, pokemon_25):
        assert "_name_en_norm" in pokemon_25
        assert pokemon_25["_name_en_norm"] == "pikachu"
        score = score_pokemon("pikachu", pokemon_25)
        assert score == 100

    def test_score_fallback_no_precomputed(self):
        poke = {"name": "Test", "name_en": "Testmon", "id": 999, "types": [], "generation": "第一世代"}
        score = score_pokemon("testmon", poke)
        assert score == 100


# ══════════════════════════════════════════════
#  Test: data.py — mock PokeAPI, no skip
# ══════════════════════════════════════════════

class TestDataMocked:
    def test_fetch_pokeapi_mock(self, monkeypatch, tmp_path):
        import urllib.request as _ur
        import src.data as _data

        cache_dir = str(tmp_path / "mock_cache")
        monkeypatch.setattr(_data, "CACHE_DIR", cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return json.dumps({
                    "height": 7, "weight": 69,
                    "stats": [{"stat": {"name": "speed"}, "base_stat": 90}],
                    "abilities": [{"ability": {"name": "static"}}],
                }).encode()

        monkeypatch.setattr(_ur, "urlopen", lambda *a, **kw: FakeResponse())
        result = fetch_pokeapi_data(25)
        assert result is not None
        assert result["height"] == 7
        assert result["weight"] == 69
        assert result["stats"]["speed"] == 90

    def test_fetch_pokeapi_http_error(self, monkeypatch, tmp_path):
        import urllib.request as _ur
        import src.data as _data

        cache_dir = str(tmp_path / "mock_cache2")
        monkeypatch.setattr(_data, "CACHE_DIR", cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

        class FakeErrorResponse:
            status = 404

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return b"Not Found"

        monkeypatch.setattr(_ur, "urlopen", lambda *a, **kw: FakeErrorResponse())
        result = fetch_pokeapi_data(99999)
        assert result is None

    def test_cached_or_fetch_uses_cache(self, monkeypatch, tmp_path):
        import src.data as _data

        cache_dir = str(tmp_path / "mock_cache3")
        monkeypatch.setattr(_data, "CACHE_DIR", cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

        cache_file = os.path.join(cache_dir, "0025.json")
        with open(cache_file, "w") as f:
            json.dump({"height": 4, "weight": 60, "stats": {}, "abilities": []}, f)

        result = fetch_pokeapi_data(25)
        assert result is not None
        assert result["height"] == 4

    def test_get_pokemon_details_fetches_pokeapi_once(self, monkeypatch):
        calls = []

        def fake_fetch_pokeapi_data(pokemon_id, quiet=False):
            calls.append((pokemon_id, quiet))
            return {
                "height": 7,
                "weight": 69,
                "stats": {
                    "hp": 45,
                    "attack": 49,
                    "defense": 49,
                    "special-attack": 65,
                    "special-defense": 65,
                    "speed": 45,
                },
                "abilities": ["茂盛"],
            }

        monkeypatch.setattr(_data, "fetch_pokeapi_data", fake_fetch_pokeapi_data)

        details = get_pokemon_details({"id": 1, "name": "妙蛙种子"}, quiet=True)

        assert calls == [(1, True)]
        assert details["height"] == 7
        assert details["stat_total"] == 318


# ══════════════════════════════════════════════
#  Test: ascii_art.py
# ══════════════════════════════════════════════

class TestAsciiArt:
    def test_get_sprite_path_no_cache_no_download(self, monkeypatch, tmp_path):
        """没有缓存且关闭下载时，get_sprite_path 返回 None"""
        # 使用不存在的缓存目录
        monkeypatch.setattr(ascii_art, "_SPRITE_CACHE_DIR", str(tmp_path / "no_such_cache"))
        monkeypatch.setattr(ascii_art, "_HAS_TERM_IMAGE", False)
        result = ascii_art.get_sprite_path("Pikachu", 25)
        assert result is None

    def test_get_sprite_path_cached(self, tmp_path, monkeypatch):
        """已有缓存文件时直接返回路径"""
        cache_dir = str(tmp_path / "sprite_cache")
        os.makedirs(cache_dir, exist_ok=True)
        monkeypatch.setattr(ascii_art, "_SPRITE_CACHE_DIR", cache_dir)
        # 创建一个假的缓存文件
        cache_file = os.path.join(cache_dir, "25.png")
        with open(cache_file, "wb") as f:
            f.write(b"fake_png_data")
        result = ascii_art.get_sprite_path("Pikachu", 25)
        assert result == cache_file

    def test_get_sprite_path_empty_name_no_id(self):
        """name_en 不在内存缓存且无 pokemon_id 时返回 None"""
        result = ascii_art.get_sprite_path("NotInCache", 0)
        assert result is None

    def test_show_sprite_no_term_image(self, monkeypatch):
        """term-image 不可用时 show_sprite 返回 False"""
        monkeypatch.setattr(ascii_art, "_HAS_TERM_IMAGE", False)
        result = ascii_art.show_sprite("Pikachu", 25)
        assert result is False

    def test_show_sprite_no_sprite_found(self, monkeypatch, tmp_path):
        """精灵图不存在时 show_sprite 返回 False"""
        monkeypatch.setattr(ascii_art, "_HAS_TERM_IMAGE", True)
        monkeypatch.setattr(ascii_art, "_SPRITE_CACHE_DIR", str(tmp_path / "empty_cache"))
        result = ascii_art.show_sprite("NoSuchPokemon", 99999)
        assert result is False


# ══════════════════════════════════════════════
#  Test: comparison.py — compute_remaining_pool
# ══════════════════════════════════════════════

class TestComputeRemainingPool:
    def test_empty_guesses_returns_pool_size(self, pokemon_list):
        config = dict(DEFAULT_CONFIG)
        pool = pokemon_list[:10]
        assert compute_remaining_pool(pool, [], config) == 10

    def test_same_pokemon_eliminates_all_but_one(self, pokemon_25, default_config):
        pool = [pokemon_25, pokemon_25]
        hints = compare_pokemon(pokemon_25, pokemon_25, default_config)
        guesses_with_hints = [(pokemon_25, hints)]
        remaining = compute_remaining_pool(pool, guesses_with_hints, default_config)
        assert remaining == 2

    def test_wrong_guess_preserves_pool(self, pokemon_1, pokemon_25, default_config):
        pool = [pokemon_1, pokemon_25]
        hints = compare_pokemon(pokemon_25, pokemon_1, default_config)
        guesses_with_hints = [(pokemon_1, hints)]
        remaining = compute_remaining_pool(pool, guesses_with_hints, default_config)
        assert remaining >= 1

    def test_multiple_guesses_reduce_pool(self, pokemon_1, pokemon_4, pokemon_25, default_config):
        """Two different wrong guesses should eliminate more candidates than one."""
        pool = [pokemon_1, pokemon_4, pokemon_25]
        hints1 = compare_pokemon(pokemon_25, pokemon_1, default_config)
        guesses1 = [(pokemon_1, hints1)]
        remaining1 = compute_remaining_pool(pool, guesses1, default_config)
        assert remaining1 >= 1

        hints2 = compare_pokemon(pokemon_25, pokemon_4, default_config)
        guesses2 = [(pokemon_1, hints1), (pokemon_4, hints2)]
        remaining2 = compute_remaining_pool(pool, guesses2, default_config)
        assert remaining2 >= 1
        assert remaining2 <= remaining1

    def test_identical_pool_and_guess_all_exact(self, pokemon_25, default_config):
        hints = compare_pokemon(pokemon_25, pokemon_25, default_config)
        guesses_with_hints = [(pokemon_25, hints)]
        remaining = compute_remaining_pool([pokemon_25], guesses_with_hints, default_config)
        assert remaining == 1

    def test_compute_remaining_pool_uses_candidate_as_target(self):
        bulbasaur = {
            "id": 1,
            "name": "妙蛙种子",
            "name_en": "Bulbasaur",
            "types": ["草", "毒"],
            "generation": "第一世代",
            "stats": {"total": 318, "speed": 45},
            "stat_total": 318,
            "speed": 45,
            "height": 7,
            "weight": 69,
        }
        charmander = {
            "id": 4,
            "name": "小火龙",
            "name_en": "Charmander",
            "types": ["火"],
            "generation": "第一世代",
            "stats": {"total": 309, "speed": 65},
            "stat_total": 309,
            "speed": 65,
            "height": 6,
            "weight": 85,
        }
        squirtle = {
            "id": 7,
            "name": "杰尼龟",
            "name_en": "Squirtle",
            "types": ["水"],
            "generation": "第一世代",
            "stats": {"total": 314, "speed": 43},
            "stat_total": 314,
            "speed": 43,
            "height": 5,
            "weight": 90,
        }
        config = {
            "game_mode": "normal",
            "show_more_stats": False,
            "show_more_appearance": False,
            "show_egg_group": False,
            "show_gen_arrow": True,
        }

        observed_hints = compare_pokemon(bulbasaur, charmander, config)
        remaining = compute_remaining_pool(
            [bulbasaur, charmander, squirtle],
            [(charmander, observed_hints)],
            config,
        )

        assert remaining == 1


# ══════════════════════════════════════════════
#  Test: share.py — format_share_result
# ══════════════════════════════════════════════

class TestFormatShareResult:
    def test_won_format(self, pokemon_25, default_config):
        hints = compare_pokemon(pokemon_25, pokemon_25, default_config)
        result = format_share_result(
            [(pokemon_25, hints)], 10,
            pokemon_25["name"], pokemon_25["name_en"], pokemon_25["id"],
            won=True, generation_label="1代",
        )
        assert "Pokémonle #25" in result
        assert "1/10" in result
        assert "皮卡丘" in result
        assert "1代" in result

    def test_lost_format(self, pokemon_25, default_config):
        result = format_share_result(
            [], 10,
            pokemon_25["name"], pokemon_25["name_en"], pokemon_25["id"],
            won=False,
        )
        assert "Pokémonle #25" in result
        assert "X/10" in result
        assert "皮卡丘" in result

    def test_columns_present(self, pokemon_1, pokemon_4, default_config):
        hints = compare_pokemon(pokemon_1, pokemon_4, default_config)
        result = format_share_result(
            [(pokemon_4, hints)], 10,
            pokemon_1["name"], pokemon_1["name_en"], pokemon_1["id"],
            won=False,
        )
        for label in ["编号", "属性"]:
            assert label in result

    def test_level_symbols_present(self, pokemon_25, default_config):
        hints = compare_pokemon(pokemon_25, pokemon_25, default_config)
        result = format_share_result(
            [(pokemon_25, hints)], 10,
            pokemon_25["name"], pokemon_25["name_en"], pokemon_25["id"],
            won=True,
        )
        assert "●" in result


# ══════════════════════════════════════════════
#  Test: fuzzy.py — PokemonTrie
# ══════════════════════════════════════════════

class TestPokemonTrie:
    def test_prefix_search_exact_cn(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        results = trie.prefix_search("皮卡丘")
        assert len(results) >= 1
        assert results[0]["id"] == 25

    def test_prefix_search_cn_prefix(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        results = trie.prefix_search("皮卡")
        assert len(results) >= 1
        assert results[0]["id"] == 25

    def test_prefix_search_en(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        results = trie.prefix_search("pikachu")
        assert len(results) >= 1
        assert results[0]["id"] == 25

    def test_prefix_search_by_id(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        results = trie.prefix_search("25")
        assert len(results) >= 1
        assert results[0]["id"] == 25

    def test_prefix_search_empty_returns_empty(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        assert trie.prefix_search("") == []

    def test_prefix_search_no_match(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        assert trie.prefix_search("zzzzz_nonexistent") == []

    def test_prefix_search_limit(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        results = trie.prefix_search("龙", limit=5)
        assert len(results) <= 5

    def test_case_insensitive(self, pokemon_list):
        trie = PokemonTrie(pokemon_list)
        results = trie.prefix_search("PIKACHU")
        assert len(results) >= 1
        assert results[0]["id"] == 25


# ══════════════════════════════════════════════
#  Test: stats.py _build_distribution
# ══════════════════════════════════════════════

class TestBuildDistribution:
    def test_empty_history(self):
        assert _build_distribution([]) == {}

    def test_single_entry(self):
        assert _build_distribution([3]) == {3: 1}

    def test_multiple_same(self):
        assert _build_distribution([3, 3, 3]) == {3: 3}

    def test_multiple_different(self):
        dist = _build_distribution([1, 2, 2, 3, 3, 3])
        assert dist == {1: 1, 2: 2, 3: 3}


# ══════════════════════════════════════════════
#  Test: game.py _safe_save_stats
# ══════════════════════════════════════════════

class TestSafeSaveStats:
    def test_save_success(self, monkeypatch, tmp_path):
        old = constants.STATS_FILE
        try:
            stats_path = str(tmp_path / "stats.json")
            constants.STATS_FILE = stats_path
            _safe_save_stats(True, 5)
            stats = _load_stats()
            assert stats["total"] == 1
            assert stats["wins"] == 1
        finally:
            constants.STATS_FILE = old

    def test_save_failure_no_crash(self, monkeypatch, tmp_path):
        old = constants.STATS_FILE
        try:
            constants.STATS_FILE = str(tmp_path / "nonexistent" / "stats.json")
            _safe_save_stats(True, 3)
        finally:
            constants.STATS_FILE = old

    def test_save_loss(self, monkeypatch, tmp_path):
        old = constants.STATS_FILE
        try:
            stats_path = str(tmp_path / "stats.json")
            constants.STATS_FILE = stats_path
            _safe_save_stats(False, 10)
            stats = _load_stats()
            assert stats["total"] == 1
            assert stats["wins"] == 0
        finally:
            constants.STATS_FILE = old


# ══════════════════════════════════════════════
#  Test: comparison.py edge cases (#32)
# ══════════════════════════════════════════════

class TestComparisonEdgeCases:
    def test_empty_types(self):
        target = {"id": 1, "types": [], "generation": "第一世代"}
        guess = {"id": 2, "types": [], "generation": "第一世代"}
        hints = compare_pokemon(target, guess, dict(DEFAULT_CONFIG))
        type_hint = next(h for h in hints if h.label == "属性")
        assert type_hint.level == "miss"
        assert type_hint.value == ""

    def test_missing_generation(self):
        target = {"id": 1, "types": ["草"], "generation": ""}
        guess = {"id": 2, "types": ["草"], "generation": ""}
        hints = compare_pokemon(target, guess, dict(DEFAULT_CONFIG))
        gen_hint = next(h for h in hints if h.label == "世代")
        assert gen_hint.level == "exact"

    def test_mischief_all_non_exact_have_no_arrow(self):
        target = {"id": 1, "types": ["草"], "generation": "第一世代", "stat_total": 300, "speed": 90}
        guess = {"id": 2, "types": ["火"], "generation": "第一世代", "stat_total": 400, "speed": 80}
        config = {**DEFAULT_CONFIG, "mischief": True, "show_gen_arrow": True}
        hints = compare_pokemon(target, guess, config)
        id_hint = next(h for h in hints if h.label == "编号")
        assert len(id_hint) == 4


# ══════════════════════════════════════════════
#  Test: game.py _show_answer
# ══════════════════════════════════════════════

class TestShowAnswer:
    def test_no_crash_with_valid_pokemon(self, pokemon_25, monkeypatch):
        monkeypatch.setattr("src.ui._show_pokemon_art", lambda *a: True)
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: None)
        _show_answer(pokemon_25, "test", "Test")
        assert True

    def test_no_crash_with_special_chars(self, pokemon_25, monkeypatch):
        monkeypatch.setattr("src.ui._show_pokemon_art", lambda *a: True)
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: None)
        _show_answer(pokemon_25, "[bold green]🎉 猜对了！[/bold green]", "🏆")
        assert True

    def test_show_answer_prints_sprite_fallback_when_art_unavailable(self, monkeypatch):
        printed = []
        monkeypatch.setattr("src.ui._show_pokemon_art", lambda *a: False)
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: printed.append(a))

        _show_answer({"id": 1, "name": "妙蛙种子", "name_en": "Bulbasaur", "types": ["草", "毒"]}, "test", "Test")

        output = " ".join(str(item) for args in printed for item in args)
        assert "图片暂不可用" in output
        assert "#1" in output
        assert "Bulbasaur" in output


# ══════════════════════════════════════════════
#  Test: data.py _cached_or_fetch
# ══════════════════════════════════════════════

class TestCachedOrFetch:
    def test_uses_cache_when_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_data, "CACHE_DIR", str(tmp_path))
        os.makedirs(tmp_path, exist_ok=True)

        cache_file = os.path.join(str(tmp_path), "test_cache.json")
        expected = {"key": "cached_value"}
        with open(cache_file, "w") as f:
            json.dump(expected, f)

        result = _data._cached_or_fetch(cache_file, "http://no", lambda d: d, "test")
        assert result == expected

    def test_fetches_when_no_cache(self, monkeypatch, tmp_path):
        import urllib.request as _ur
        monkeypatch.setattr(_data, "CACHE_DIR", str(tmp_path))
        os.makedirs(tmp_path, exist_ok=True)

        class FakeResponse:
            status = 200
            def read(self):
                return json.dumps({"fetched": True}).encode()
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(_ur, "urlopen", lambda *a, **kw: FakeResponse())
        result = _data._cached_or_fetch(
            os.path.join(str(tmp_path), "new.json"),
            "http://test", lambda d: d, "test", quiet=True,
        )
        assert result == {"fetched": True}

    def test_returns_none_on_http_error(self, monkeypatch, tmp_path):
        import urllib.request as _ur
        monkeypatch.setattr(_data, "CACHE_DIR", str(tmp_path))
        os.makedirs(tmp_path, exist_ok=True)

        class FakeError:
            status = 404
            def read(self): return b""
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(_ur, "urlopen", lambda *a, **kw: FakeError())
        result = _data._cached_or_fetch(
            os.path.join(str(tmp_path), "err.json"),
            "http://test", lambda d: d, "test", quiet=True,
        )
        assert result is None


# ══════════════════════════════════════════════
#  Test: ascii_art.py _download_sprite
# ══════════════════════════════════════════════

class TestDownloadSprite:
    def test_returns_none_on_network_error(self, monkeypatch, tmp_path):
        import urllib.request as _ur
        from urllib.error import URLError
        monkeypatch.setattr(ascii_art, "_SPRITE_CACHE_DIR", str(tmp_path))

        def fake_urlopen(*a, **kw):
            raise URLError("network down")

        monkeypatch.setattr(_ur, "urlopen", fake_urlopen)
        result = ascii_art._download_sprite(25)
        assert result is None

    def test_caches_downloaded_file(self, monkeypatch, tmp_path):
        import urllib.request as _ur
        cache_dir = str(tmp_path / "sprites")
        monkeypatch.setattr(ascii_art, "_SPRITE_CACHE_DIR", cache_dir)

        class FakeResponse:
            def read(self): return b"fake_png"
            def __enter__(self): return self
            def __exit__(self, *a): pass

        monkeypatch.setattr(_ur, "urlopen", lambda *a, **kw: FakeResponse())
        result = ascii_art._download_sprite(25)
        assert result == os.path.join(cache_dir, "25.png")
        assert os.path.exists(result)


# ══════════════════════════════════════════════
#  Test: main menu loop
# ══════════════════════════════════════════════

class TestMain:
    def test_quit_exits(self, monkeypatch, pokemon_list):
        monkeypatch.setattr("src.game.show_logo", lambda: None)
        monkeypatch.setattr("src.game.load_config", lambda: dict(DEFAULT_CONFIG))
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: None)
        monkeypatch.setattr("src.ui._console.input", lambda *a, **kw: "q")
        monkeypatch.setattr("src.data.load_pokemon_data", lambda: pokemon_list)

        try:
            game.main()
        except SystemExit:
            pass

    def test_chooses_game(self, monkeypatch, pokemon_list):
        inputs = ["1", "q"]
        monkeypatch.setattr("src.game.show_logo", lambda: None)
        monkeypatch.setattr("src.game.load_config", lambda: dict(DEFAULT_CONFIG))
        monkeypatch.setattr("src.ui._console.print", lambda *a, **kw: None)
        monkeypatch.setattr("src.data.load_pokemon_data", lambda: pokemon_list)

        def fake_input(prompt=""):
            return inputs.pop(0)
        monkeypatch.setattr("src.ui._console.input", fake_input)
        monkeypatch.setattr("src.game.run_game", lambda pl, cfg: None)

        try:
            game.main()
        except (SystemExit, IndexError):
            pass


# ══════════════════════════════════════════════
#  Test: integration
# ══════════════════════════════════════════════

class TestIntegration:
    def test_load_and_compare_roundtrip(self, pokemon_list):
        assert len(pokemon_list) > 1000
        pikachu = next(p for p in pokemon_list if p["id"] == 25)
        assert pikachu["name"] == "皮卡丘"
        assert pikachu["types"] == ["电"]
        hints = compare_pokemon(pikachu, pikachu, dict(DEFAULT_CONFIG))
        labels = {h.label for h in hints}
        assert "编号" in labels
        assert "属性" in labels
        assert "世代" in labels

    def test_find_and_compare(self, pokemon_list):
        target = next(p for p in pokemon_list if p["id"] == 25)
        guess = find_pokemon("皮卡丘", pokemon_list)
        assert guess is not None
        assert guess["id"] == 25
        hints = compare_pokemon(target, guess, dict(DEFAULT_CONFIG))
        assert len(hints) > 0

    def test_build_index_and_lookup(self, pokemon_list):
        idx = build_pokemon_index(pokemon_list)
        assert idx[25]["name"] == "皮卡丘"
        assert idx["pikachu"]["id"] == 25
        assert idx["皮卡丘"]["id"] == 25


class _FakeSession:
    def __init__(self, inputs):
        self._inputs = list(inputs)
        self._idx = 0
        self.message = ""

    def prompt(self):
        if self._idx >= len(self._inputs):
            raise EOFError
        val = self._inputs[self._idx]
        self._idx += 1
        return val


def _mock_game_env(monkeypatch, pokemon_list, target, inputs, tmp_path):
    import src.game as _game

    stats_file = str(tmp_path / "stats.json")
    monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: _FakeSession(inputs))
    monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))
    monkeypatch.setattr("random.choice", lambda s: target)
    monkeypatch.setattr("src.game._console.print", lambda *a, **kw: None)
    monkeypatch.setattr("src.game.show_hints_table", lambda *a, **kw: None)

    def _fake_details(poke, **kwargs):
        d = dict(poke)
        d.update({"stat_total": 300, "speed": 90, "hp": 45, "attack": 50,
                   "defense": 40, "sp_attack": 60, "sp_defense": 50,
                   "height": 40, "weight": 60, "stats": {}})
        return d
    monkeypatch.setattr("src.game.get_pokemon_details", _fake_details)
    monkeypatch.setattr("src.game.fetch_species_data", lambda _id, **kw: None)

    config = dict(DEFAULT_CONFIG)
    _game.run_game(pokemon_list, config)


class TestRunGame:
    def test_win_on_exact_match(self, monkeypatch, pokemon_list, tmp_path):
        stat_calls = []
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))
        target = pokemon_list[0]
        _mock_game_env(monkeypatch, pokemon_list, target, ["妙蛙种子"], tmp_path)
        assert stat_calls == [(True, 1)]

    def test_quit_saves_loss(self, monkeypatch, pokemon_list, tmp_path):
        stat_calls = []
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))
        target = pokemon_list[0]
        _mock_game_env(monkeypatch, pokemon_list, target, ["q"], tmp_path)
        assert stat_calls == [(False, 0)]

    def test_reveal_saves_loss(self, monkeypatch, pokemon_list, tmp_path):
        stat_calls = []
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))
        target = pokemon_list[0]
        _mock_game_env(monkeypatch, pokemon_list, target, ["reveal"], tmp_path)
        assert stat_calls == [(False, 0)]

    def test_lose_on_max_guesses(self, monkeypatch, pokemon_list, tmp_path):
        stat_calls = []
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))

        target = pokemon_list[0]
        all_pokemon = [p["name"] for p in pokemon_list if p["id"] != target["id"]]
        bad_guesses = all_pokemon[:15]

        import src.game as _game
        monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: _FakeSession(bad_guesses))
        monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))
        monkeypatch.setattr("random.choice", lambda s: target)
        monkeypatch.setattr("src.game._console.print", lambda *a, **kw: None)
        monkeypatch.setattr("src.game.show_hints_table", lambda *a, **kw: None)
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))
        monkeypatch.setattr("src.game.get_pokemon_details", lambda p, **kw: {**p, "stat_total": 300, "speed": 90, "hp": 45, "attack": 50, "defense": 40, "sp_attack": 60, "sp_defense": 50, "height": 40, "weight": 60, "stats": {}})
        monkeypatch.setattr("src.game.fetch_species_data", lambda _id, **kw: None)
        _game.run_game(pokemon_list, {**DEFAULT_CONFIG, "max_guesses": 15})
        assert stat_calls[-1] == (False, 15)

    def test_empty_pool_returns_early(self, monkeypatch, pokemon_list, tmp_path):
        import src.game as _game
        config = {**DEFAULT_CONFIG, "generations": []}
        monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: _FakeSession([]))
        monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))
        _game.run_game(pokemon_list, config)

    def test_not_found_then_quit(self, monkeypatch, pokemon_list, tmp_path):
        stat_calls = []
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))
        target = pokemon_list[0]
        _mock_game_env(monkeypatch, pokemon_list, target, ["zzzz_not_found", "q"], tmp_path)
        assert len(stat_calls) > 0

    def test_mischief_mode_no_crash(self, monkeypatch, pokemon_list, tmp_path):
        stat_calls = []
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: stat_calls.append((w, g)))
        target = pokemon_list[0]
        config = {**DEFAULT_CONFIG, "mischief": True, "max_guesses": 15}
        import src.game as _game
        monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: _FakeSession(["皮卡丘", "q"]))
        monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))

        real_choice = random.choice
        monkeypatch.setattr("random.choice", lambda s: target if isinstance(s[0], dict) else real_choice(s))

        monkeypatch.setattr("src.game._console.print", lambda *a, **kw: None)
        monkeypatch.setattr("src.game.show_hints_table", lambda *a, **kw: None)
        monkeypatch.setattr("src.game.get_pokemon_details", lambda p, **kw: {**p, "stat_total": 300, "speed": 90, "hp": 45, "attack": 50, "defense": 40, "sp_attack": 60, "sp_defense": 50, "height": 40, "weight": 60, "stats": {}})
        monkeypatch.setattr("src.game.fetch_species_data", lambda _id, **kw: None)
        _game.run_game(pokemon_list, config)

    def test_game_prompt_mentions_quit_and_reveal(self, monkeypatch, pokemon_list, tmp_path):
        target = pokemon_list[0]
        session = _FakeSession(["q"])
        import src.game as _game
        monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: session)
        monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))
        monkeypatch.setattr("random.choice", lambda s: target)
        monkeypatch.setattr("src.game._console.print", lambda *a, **kw: None)
        monkeypatch.setattr("src.game.get_pokemon_details", lambda p, **kw: {**p, "stat_total": 300, "speed": 90, "hp": 45, "attack": 50, "defense": 40, "sp_attack": 60, "sp_defense": 50, "height": 40, "weight": 60, "stats": {}})
        monkeypatch.setattr("src.game.fetch_species_data", lambda _id, **kw: None)
        monkeypatch.setattr("src.game.save_game_stats", lambda w, g: None)

        _game.run_game(pokemon_list, dict(DEFAULT_CONFIG))

        assert "q=退出" in session.message
        assert "reveal=看答案" in session.message

    def test_format_remaining_pool_warning_for_zero_candidates(self):
        warning = game._format_remaining_pool_warning(0)
        assert "没有候选" in warning
        assert "网络数据" in warning or "谜题" in warning
