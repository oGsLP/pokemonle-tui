"""
 比较逻辑 — 目标宝可梦和猜测宝可梦之间的对比，生成提示列表
 """

from typing import cast

import constants
from constants import GEN_MAP, Hint
from poketypes import ConfigDict, PokemonData

GAME_MODE_PRESETS: dict[str, dict] = cast(dict[str, dict], constants.GAME_MODE_PRESETS)


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
    target_id = cast(int, target["id"])
    guess_id = cast(int, guess["id"])
    diff = target_id - guess_id
    if diff == 0:
        hints.append(Hint("编号", f"#{target_id:04d}", "exact"))
    elif abs(diff) <= preset["id_range"]:
        hints.append(Hint("编号", f"#{guess_id:04d}", "close", "↑" if diff > 0 else "↓"))
    else:
        hints.append(Hint("编号", f"#{guess_id:04d}", "far", "↑" if diff > 0 else "↓"))

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
        target_stat_total = cast(int, target["stat_total"])
        guess_stat_total = cast(int, guess["stat_total"])
        diff_st = target_stat_total - guess_stat_total
        arrow = "↑" if diff_st > 0 else "↓"
        if diff_st == 0:
            hints.append(Hint("种族值", str(guess_stat_total), "exact"))
        elif abs(diff_st) <= preset["stat_range"]:
            hints.append(Hint("种族值", str(guess_stat_total), "close", arrow))
        else:
            hints.append(Hint("种族值", str(guess_stat_total), "far", arrow))

    # ── 速度 ──
    if "speed" in target and "speed" in guess:
        target_speed = cast(int, target["speed"])
        guess_speed = cast(int, guess["speed"])
        diff_sp = target_speed - guess_speed
        arrow = "↑" if diff_sp > 0 else "↓"
        if diff_sp == 0:
            hints.append(Hint("速度", str(guess_speed), "exact"))
        elif abs(diff_sp) <= preset["speed_range"]:
            hints.append(Hint("速度", str(guess_speed), "close", arrow))
        else:
            hints.append(Hint("速度", str(guess_speed), "far", arrow))

    # ── 更多种族值 (HP/攻击/防御/特攻/特防) ──
    if config.get("show_more_stats"):
        for stat_key, stat_cn in [("hp", "HP"), ("attack", "攻击"), ("defense", "防御"),
                                  ("sp_attack", "特攻"), ("sp_defense", "特防")]:
            if stat_key in target and stat_key in guess:
                target_stat = cast(int, target[stat_key])
                guess_stat = cast(int, guess[stat_key])
                diff_v = target_stat - guess_stat
                arrow = "↑" if diff_v > 0 else "↓"
                if diff_v == 0:
                    hints.append(Hint(stat_cn, str(guess_stat), "exact"))
                elif abs(diff_v) <= preset["detail_range"]:
                    hints.append(Hint(stat_cn, str(guess_stat), "close", arrow))
                else:
                    hints.append(Hint(stat_cn, str(guess_stat), "far", arrow))

    # ── 身高 ──
    if "height" in target and "height" in guess:
        target_height = cast(int, target["height"])
        guess_height = cast(int, guess["height"])
        diff_h = target_height - guess_height
        arrow = "↑" if diff_h > 0 else "↓"
        h2 = guess_height / 10
        if diff_h == 0:
            hints.append(Hint("身高", f"{h2:.1f}m", "exact"))
        elif abs(diff_h) <= preset["height_range"]:
            hints.append(Hint("身高", f"{h2:.1f}m", "close", arrow))
        else:
            hints.append(Hint("身高", f"{h2:.1f}m", "far", arrow))

    # ── 体重 ──
    if "weight" in target and "weight" in guess:
        target_weight = cast(int, target["weight"])
        guess_weight = cast(int, guess["weight"])
        diff_w = target_weight - guess_weight
        arrow = "↑" if diff_w > 0 else "↓"
        w2 = guess_weight / 10
        if diff_w == 0:
            hints.append(Hint("体重", f"{w2:.1f}kg", "exact"))
        elif abs(diff_w) <= preset["weight_range"]:
            hints.append(Hint("体重", f"{w2:.1f}kg", "close", arrow))
        else:
            hints.append(Hint("体重", f"{w2:.1f}kg", "far", arrow))

    # ── 更多外形信息 ──
    if config.get("show_more_appearance") and "height" in target and "height" in guess:
        h_ratio = target_height / max(guess_height, 1)
        if h_ratio > 1.5:
            hints.append(Hint("体型", "更大", "miss"))
        elif h_ratio < 0.67:
            hints.append(Hint("体型", "更小", "miss"))
        else:
            hints.append(Hint("体型", "差不多", "partial"))

    return hints
