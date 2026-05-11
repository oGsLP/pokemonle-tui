"""0.2.2 polish regression tests.

These tests cover the focused 0.2.2 fixes without further growing the
legacy all-in-one test module.
"""
from io import StringIO
from typing import cast

from rich.console import Console

import src.data as data_module
import src.game as game
import src.ui as ui
from src.comparison import compare_pokemon, compute_remaining_pool
from src.config import _validate_config
from src.constants import ALL_GENERATIONS, DEFAULT_CONFIG, Hint
from src.data import get_pokemon_details
from src.poketypes import ConfigDict, GuessRecord, HintRecord, PokemonEntry
from src.ui import _format_hint, _show_answer


class _FakeSession:
    def __init__(self, inputs):
        self._inputs = list(inputs)
        self._idx = 0
        self.message = ""

    def prompt(self):
        if self._idx >= len(self._inputs):
            raise EOFError
        value = self._inputs[self._idx]
        self._idx += 1
        return value


def _style_text(style: object) -> str:
    return str(style)


def _bulbasaur() -> PokemonEntry:
    return {
        "id": 1,
        "name": "妙蛙种子",
        "name_en": "Bulbasaur",
        "name_jp": "フシギダネ",
        "index": "1",
        "types": ["草", "毒"],
        "generation": "第一世代",
        "stats": {"total": 318, "speed": 45},
        "stat_total": 318,
        "speed": 45,
        "height": 7,
        "weight": 69,
    }


def _charmander() -> PokemonEntry:
    return {
        "id": 4,
        "name": "小火龙",
        "name_en": "Charmander",
        "name_jp": "ヒトカゲ",
        "index": "4",
        "types": ["火"],
        "generation": "第一世代",
        "stats": {"total": 309, "speed": 65},
        "stat_total": 309,
        "speed": 65,
        "height": 6,
        "weight": 85,
    }


def _squirtle() -> PokemonEntry:
    return {
        "id": 7,
        "name": "杰尼龟",
        "name_en": "Squirtle",
        "name_jp": "ゼニガメ",
        "index": "7",
        "types": ["水"],
        "generation": "第一世代",
        "stats": {"total": 314, "speed": 43},
        "stat_total": 314,
        "speed": 43,
        "height": 5,
        "weight": 90,
    }


class TestHintSymbols:
    def test_format_hint_prefixes_accessible_symbols(self):
        assert "●" in _format_hint("编号", "#0001", "exact").plain
        assert "◐" in _format_hint("编号", "#0002", "close", "↑").plain
        assert "○" in _format_hint("身高", "1.5m", "far", "↓").plain

    def test_type_partial_keeps_matched_and_unmatched_styles(self):
        text = _format_hint("属性", "草/飞行", "partial", "草")

        assert "◐" in text.plain
        assert "草" in text.plain
        assert "飞行" in text.plain
        assert any("white on" in _style_text(span.style) for span in text.spans)
        assert any("dim" in _style_text(span.style) for span in text.spans)


class TestNarrowTableRendering:
    def test_show_hints_table_renders_with_narrow_console(self, monkeypatch):
        output = StringIO()
        monkeypatch.setattr(ui, "_console", Console(file=output, width=60, force_terminal=False))
        guesses: list[GuessRecord] = [
            (
                {
                    "id": 1,
                    "name": "妙蛙种子",
                    "name_en": "Bulbasaur",
                    "name_jp": "フシギダネ",
                    "index": "1",
                    "types": ["草", "毒"],
                    "generation": "第一世代",
                },
                [
                    Hint("编号", "1", "exact"),
                    Hint("属性", "草/毒", "partial", "草"),
                    Hint("世代", "1", "exact"),
                    Hint("种族值", "318", "close", "↑"),
                    Hint("速度", "45", "far", "↓"),
                ],
            )
        ]
        config: ConfigDict = {
            "reverse_order": False,
            "show_more_stats": False,
            "show_more_appearance": False,
            "show_egg_group": False,
        }

        ui.show_hints_table(guesses, 10, config, pool_size=12)
        rendered = output.getvalue()

        assert "猜测记录" in rendered
        assert "Bulbasaur" in rendered or "妙蛙" in rendered


class TestConfigAndSettingsPolish:
    def test_empty_generations_validate_as_all_generations(self):
        config = _validate_config({"generations": []})

        assert config["generations"] == ALL_GENERATIONS

    def test_settings_text_explains_generation_reset(self, monkeypatch):
        output = []
        monkeypatch.setattr("src.ui._console.print", lambda *args, **kwargs: output.extend(str(arg) for arg in args))
        monkeypatch.setattr("src.ui._console.input", lambda *args, **kwargs: "q")

        ui.show_settings(dict(DEFAULT_CONFIG))

        assert "n[/cyan]=重置为全部世代" in "\n".join(output)

    def test_settings_copy_names_egg_group_without_capture_rate(self, monkeypatch):
        output = []
        monkeypatch.setattr("src.ui._console.print", lambda *args, **kwargs: output.extend(str(arg) for arg in args))
        monkeypatch.setattr("src.ui._console.input", lambda *args, **kwargs: "q")

        ui.show_settings(dict(DEFAULT_CONFIG))
        rendered = "\n".join(output)

        assert "显示蛋组信息" in rendered
        assert "捕获率" not in rendered


class TestLogoVersion:
    def test_logo_uses_0_2_2_version(self, monkeypatch):
        output = StringIO()
        monkeypatch.setattr(ui, "_console", Console(file=output, force_terminal=False))

        ui.show_logo()
        rendered = output.getvalue()

        assert "0.2.2" in rendered
        assert "CLI v2" not in rendered


class TestDataFetchPolish:
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

        monkeypatch.setattr(data_module, "fetch_pokeapi_data", fake_fetch_pokeapi_data)

        details = get_pokemon_details(
            {
                "id": 1,
                "name": "妙蛙种子",
                "name_en": "Bulbasaur",
                "name_jp": "フシギダネ",
                "index": "1",
                "types": ["草", "毒"],
                "generation": "第一世代",
            },
            quiet=True,
        )

        assert calls == [(1, True)]
        assert details.get("height") == 7
        assert details.get("stat_total") == 318


class TestRemainingPoolPolish:
    def test_compute_remaining_pool_uses_candidate_as_target(self):
        config: ConfigDict = {
            "game_mode": "normal",
            "show_more_stats": False,
            "show_more_appearance": False,
            "show_egg_group": False,
            "show_gen_arrow": True,
        }
        observed_hints = cast(list[HintRecord], compare_pokemon(_bulbasaur(), _charmander(), config))

        remaining = compute_remaining_pool(
            [_bulbasaur(), _charmander(), _squirtle()],
            [(_charmander(), observed_hints)],
            config,
        )

        assert remaining == 1


class TestAnswerFallbackPolish:
    def test_show_answer_prints_sprite_fallback_when_art_unavailable(self, monkeypatch):
        printed = []
        monkeypatch.setattr("src.ui._show_pokemon_art", lambda *args: False)
        monkeypatch.setattr("src.ui._console.print", lambda *args, **kwargs: printed.append(args))

        _show_answer(_bulbasaur(), "test", "Test")
        output = " ".join(str(item) for args in printed for item in args)

        assert "图片暂不可用" in output
        assert "#1" in output
        assert "Bulbasaur" in output


class TestGamePromptPolish:
    def test_game_prompt_mentions_quit_and_reveal(self, monkeypatch, pokemon_list):
        target = pokemon_list[0]
        session = _FakeSession(["q"])
        monkeypatch.setattr(game, "PromptSession", lambda *args, **kwargs: session)
        monkeypatch.setattr(game, "CompleteStyle", type("CompleteStyle", (), {"MULTI_COLUMN": 1}))
        monkeypatch.setattr("random.choice", lambda sequence: target)
        monkeypatch.setattr("src.game._console.print", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            "src.game.get_pokemon_details",
            lambda poke, **kwargs: {
                **poke,
                "stat_total": 300,
                "speed": 90,
                "hp": 45,
                "attack": 50,
                "defense": 40,
                "sp_attack": 60,
                "sp_defense": 50,
                "height": 40,
                "weight": 60,
                "stats": {},
            },
        )
        monkeypatch.setattr("src.game.fetch_species_data", lambda pokemon_id, **kwargs: None)
        monkeypatch.setattr("src.game.save_game_stats", lambda won, guesses: None)

        game.run_game(pokemon_list, dict(DEFAULT_CONFIG))

        assert "q=退出" in session.message
        assert "reveal=看答案" in session.message

    def test_format_remaining_pool_warning_for_zero_candidates(self):
        warning = game._format_remaining_pool_warning(0)

        assert "没有候选" in warning
        assert "网络数据" in warning or "谜题" in warning
