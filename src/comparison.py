"""
 比较逻辑 — 目标宝可梦和猜测宝可梦之间的对比，生成提示列表
 """

from typing import Callable, cast

import constants
from constants import GEN_MAP, Hint
from poketypes import ConfigDict, GuessRecord, PokemonData

GAME_MODE_PRESETS: dict[str, dict] = cast(dict[str, dict], constants.GAME_MODE_PRESETS)


def _compare_stat(
    target_val: int,
    guess_val: int,
    label: str,
    guess_display: str,
    range_key: str,
    preset: dict[str, int],
    *,
    formatter: Callable[[int], str] | None = None,
) -> Hint:
    diff = target_val - guess_val
    arrow = "↑" if diff > 0 else "↓"
    display = formatter(guess_val) if formatter else guess_display
    if diff == 0:
        return Hint(label, display, "exact")
    elif abs(diff) <= preset[range_key]:
        return Hint(label, display, "close", arrow)
    else:
        return Hint(label, display, "far", arrow)


def compare_pokemon(target: PokemonData, guess: PokemonData, config: ConfigDict) -> list[Hint]:
    """
    比较目标宝可梦和猜测宝可梦，返回提示列表。
    每个提示格式: (标签, 值, 等级, [箭头])
    等级: "exact"(✅完全匹配) | "close"/"partial"(🟡接近) | "far"/"miss"(⬛不匹配)
    """
    hints: list[Hint] = []
    mode = config.get("game_mode", "normal")
    if not isinstance(mode, str):
        mode = "normal"
    preset = GAME_MODE_PRESETS.get(mode, GAME_MODE_PRESETS["normal"])

    # ── 编号 ──
    hints.append(_compare_stat(
        cast(int, target["id"]),
        cast(int, guess["id"]),
        "编号", f"#{cast(int, guess['id']):04d}", "id_range", preset,
        formatter=lambda v: f"#{v:04d}",
    ))

    # ── 属性 ──
    target_types = cast(list[str], target["types"])
    guess_types = cast(list[str], guess["types"])
    t1 = set(target_types)
    t2 = set(guess_types)
    if t1 & t2:
        matched = "/".join(sorted(t1 & t2))
        hints.append(Hint("属性", "/".join(guess_types), "partial", matched))
    else:
        hints.append(Hint("属性", "/".join(guess_types), "miss"))

    # ── 蛋组 ──
    if config.get("show_egg_group"):
        target_egg_groups = target.get("egg_groups")
        guess_egg_groups = guess.get("egg_groups")
        if isinstance(target_egg_groups, list) and isinstance(guess_egg_groups, list) and target_egg_groups and guess_egg_groups:
            target_egg_list = cast(list[str], target_egg_groups)
            guess_egg_list = cast(list[str], guess_egg_groups)
            target_egg_set = set(target_egg_list)
            guess_egg_set = set(guess_egg_list)
            if target_egg_set == guess_egg_set:
                hints.append(Hint("蛋组", "/".join(target_egg_list), "exact"))
            elif target_egg_set & guess_egg_set:
                matched = "/".join(sorted(target_egg_set & guess_egg_set))
                hints.append(Hint("蛋组", "/".join(guess_egg_list), "partial", f"含{matched}"))
            else:
                hints.append(Hint("蛋组", "/".join(guess_egg_list), "miss"))

    # ── 世代 ──
    gen_t = cast(str, target["generation"])
    gen_g = cast(str, guess["generation"])
    if gen_t == gen_g:
        hints.append(Hint("世代", GEN_MAP.get(gen_t, (gen_t,))[0], "exact"))
    else:
        gt = GEN_MAP.get(gen_t, (gen_t, 0))[1]
        gg = GEN_MAP.get(gen_g, (gen_g, 0))[1]
        if gt and gg:
            arrow = "↑" if gt > gg else "↓"
            level = "close" if abs(gt - gg) == 1 else "far"
            if config.get("show_gen_arrow"):
                hints.append(Hint("世代", GEN_MAP.get(gen_g, (gen_g,))[0], level, arrow))
            else:
                hints.append(Hint("世代", GEN_MAP.get(gen_g, (gen_g,))[0], level))
        else:
            hints.append(Hint("世代", gen_g, "far"))

    # ── 种族值总和 ──
    if "stat_total" in target and "stat_total" in guess:
        hints.append(_compare_stat(
            cast(int, target["stat_total"]),
            cast(int, guess["stat_total"]),
            "种族值", str(cast(int, guess["stat_total"])), "stat_range", preset,
        ))

    # ── 速度 ──
    if "speed" in target and "speed" in guess:
        hints.append(_compare_stat(
            cast(int, target["speed"]),
            cast(int, guess["speed"]),
            "速度", str(cast(int, guess["speed"])), "speed_range", preset,
        ))

    # ── 更多种族值 (HP/攻击/防御/特攻/特防) ──
    if config.get("show_more_stats"):
        for stat_key, stat_cn in [("hp", "HP"), ("attack", "攻击"), ("defense", "防御"),
                                  ("sp_attack", "特攻"), ("sp_defense", "特防")]:
            if stat_key in target and stat_key in guess:
                hints.append(_compare_stat(
                    cast(int, target[stat_key]),
                    cast(int, guess[stat_key]),
                    stat_cn, str(cast(int, guess[stat_key])), "detail_range", preset,
                ))

    # ── 身高 ──
    height_available = "height" in target and "height" in guess
    if height_available:
        hints.append(_compare_stat(
            cast(int, target["height"]),
            cast(int, guess["height"]),
            "身高", f"{cast(int, guess['height']) / 10:.1f}m", "height_range", preset,
            formatter=lambda v: f"{v / 10:.1f}m",
        ))

    # ── 体重 ──
    if "weight" in target and "weight" in guess:
        hints.append(_compare_stat(
            cast(int, target["weight"]),
            cast(int, guess["weight"]),
            "体重", f"{cast(int, guess['weight']) / 10:.1f}kg", "weight_range", preset,
            formatter=lambda v: f"{v / 10:.1f}kg",
        ))

    # ── 更多外形信息 ──
    if config.get("show_more_appearance") and height_available:
        target_height = cast(int, target["height"])
        guess_height = cast(int, guess["height"])
        h_ratio = target_height / max(guess_height, 1)
        if h_ratio > 1.5:
            hints.append(Hint("体型", "更大", "miss"))
        elif h_ratio < 0.67:
            hints.append(Hint("体型", "更小", "miss"))
        else:
            hints.append(Hint("体型", "差不多", "partial"))

    return hints


def compute_remaining_pool(
    pool: list[PokemonData],
    guesses_with_hints: list[GuessRecord],
    config: ConfigDict,
) -> int:
    """Count pool members consistent with all revealed hints.

    A candidate survives if, for every previous guess, comparing
    guess → candidate produces the same hint levels as the actual
    hints revealed to the player.
    """
    if not guesses_with_hints:
        return len(pool)

    surviving = 0
    for candidate in pool:
        consistent = True
        for guess_poke, actual_hints in guesses_with_hints:
            candidate_hints = compare_pokemon(guess_poke, candidate, config)
            actual_levels = {h.label: h.level for h in actual_hints}
            candidate_levels = {h.label: h.level for h in candidate_hints}
            if actual_levels != candidate_levels:
                consistent = False
                break
        if consistent:
            surviving += 1

    return surviving
