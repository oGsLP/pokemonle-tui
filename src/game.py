"""
UI 与游戏逻辑 — logo/表格/设置面板/游戏主循环
"""
from __future__ import annotations

import os
import random
import threading
import time
from typing import cast

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align

from constants import ALL_GENERATIONS, GAME_MODE_PRESETS, GEN_MAP, Hint, TYPE_COLORS, TYPE_CN_TO_EN_MAP
from poketypes import ConfigDict, GuessRecord, HintRecord, PokemonEntry
import data as _data
from data import get_pokemon_details, fetch_species_data, build_pokemon_index
from config import load_config, save_config
from comparison import compare_pokemon, compute_remaining_pool
from fuzzy import find_pokemon, get_fuzzy_matches, PokemonCompleter
from stats import save_game_stats, get_stats_summary
from share import format_share_result
from ascii_art import show_sprite

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.shortcuts import CompleteStyle
except ImportError:
    PromptSession = None
    CompleteStyle = None


_console = Console()

# Hint label → icon mapping (matches web version: success/warning/info)
HINT_ICON = {"exact": "", "partial": "", "close": "", "miss": "", "far": ""}
HINT_TAIL = {"exact": " ✓", "partial": "", "close": "", "miss": "", "far": ""}
HINT_COLOR = {"exact": "bold green", "partial": "bold yellow", "close": "bold yellow",
              "miss": "dim", "far": "dim"}
ARROW_UP = "bold green"
ARROW_DOWN = "bold red"


def _hint_color(level: str) -> str:
    return HINT_COLOR.get(level, "white")


def _safe_save_stats(won: bool, guesses: int) -> None:
    """Save stats, logging but not crashing on failure."""
    try:
        save_game_stats(won, guesses)
    except OSError:
        pass  # Already logged in save_game_stats


def show_logo() -> None:
    logo = r"""
  ██████╗ ██╗   ██╗ █████╗  ██████╗██╗  ██╗██╗     ███████╗███████╗
  ██╔══██╗██║   ██║██╔══██╗██╔════╝██║ ██╔╝██║     ██╔════╝██╔════╝
  ██████╔╝██║   ██║███████║██║     █████╔╝ ██║     █████╗  ███████╗
  ██╔═══╝ ██║   ██║██╔══██║██║     ██╔═██╗ ██║     ██╔══╝  ╚════██║
  ██║     ╚██████╔╝██║  ██║╚██████╗██║  ██╗███████╗███████╗███████║
  ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
  ── 宝可梦猜猜猜 CLI v2 ──
"""
    _console.print(Panel(
        Align.center(Text(logo, style="bold cyan")),
        border_style="dim", box=box.ROUNDED, padding=(0, 1),
    ))


def _format_hint(label: str, val: str, level: str, extra: str = "") -> Text:
    color = _hint_color(level)
    t = Text(style=color)
    if label == "属性" and val:
        matched_types = set(extra.split("/")) if extra else set()
        for idx, type_name in enumerate(val.split("/")):
            if idx > 0:
                _ = t.append("/", style=color)
            type_key = TYPE_CN_TO_EN_MAP.get(type_name)
            type_color = TYPE_COLORS.get(type_key, color) if type_key else color
            if level == "partial" and type_name in matched_types:
                _ = t.append(type_name, style=f"white on {type_color}")
            else:
                _ = t.append(type_name, style=f"dim {type_color}")
    else:
        _ = t.append(val, style=color)
    if extra and label != "属性":
        arrow_style = ARROW_UP if extra == "↑" else ARROW_DOWN
        _ = t.append(f" {extra}", style=arrow_style)
    tail = HINT_TAIL.get(level, "")
    if tail:
        _ = t.append(tail, style="bold green")
    return t


def show_hints_table(guesses_with_hints: list[GuessRecord], max_guesses: int, config: ConfigDict, *, pool_size: int = 0) -> None:
    """显示猜测历史表格"""
    # 收集所有可能的 hint key，按顺序
    header_keys = ["编号", "属性", "世代"]
    if config.get("show_more_stats"):
        header_keys += ["HP", "攻击", "防御", "特攻", "特防"]
    header_keys += ["种族值", "速度"]
    if config.get("show_more_appearance"):
        header_keys += ["体型"]
    header_keys += ["身高", "体重"]
    if config.get("show_egg_group"):
        header_keys += ["蛋组"]

    title = f"📋 猜测记录 (第 {len(guesses_with_hints)}/{max_guesses} 次"
    if pool_size:
        title += f" | 剩余 {pool_size} 只"
    title += ")"

    table = Table(
        box=box.SIMPLE_HEAVY, border_style="dim", show_header=True,
        header_style="bold white on grey23",
        title=title,
        title_style="bold yellow",
        padding=(0, 1),
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("中文名", style="bold", width=10)
    table.add_column("英文名", style="dim", width=14)
    for k in header_keys:
        table.add_column(k, justify="center", no_wrap=True)

    rows = guesses_with_hints

    for i, (guess_poke, hints) in enumerate(rows, 1):
        hint_dict: dict[str, tuple[str, str, str]] = {}
        for h in hints:
            if len(h) == 4:
                label, val, level, extra = h
                hint_dict[label] = (val, level, extra or "")
            else:
                label, val, level = h
                hint_dict[label] = (val, level, "")

        row = [str(i), Text(guess_poke['name'], style="bold"), Text(guess_poke['name_en'])]
        for k in header_keys:
            if k in hint_dict:
                val, level, extra = hint_dict[k]
                row.append(_format_hint(k, val, level, extra))
            else:
                row.append(Text("—", style="dim"))
        table.add_row(*row)

    _console.print(table)


def show_game_stats(pokemon_count: int) -> None:
    """显示游戏统计面板"""
    _console.print(Panel(get_stats_summary(pokemon_count).strip(), border_style="dim", title="📊 Stats"))


# ══════════════════════════════════════════════
#  设置面板
# ══════════════════════════════════════════════

def show_settings(config: ConfigDict) -> ConfigDict:
    """交互式设置面板"""
    cfg = dict(config)

    if not cfg.get("generations"):
        cfg["generations"] = list(ALL_GENERATIONS)

    while True:
        _console.print(f"\n{'═' * 40}")
        _console.print("  ⚙️  设置")
        _console.print("═" * 40)

        # 游戏模式
        mode_display = {
            "normal": "普通模式 · 标准难度",
            "hard": "困难模式 · 更严格的提示范围和更少猜测次数",
            "easy": "简单模式 · 更宽松的提示范围和更多猜测次数",
        }.get(cfg.get("game_mode", "normal"), cfg.get("game_mode", "normal"))
        _console.print(f"\n  游戏模式: [yellow]{mode_display}[/yellow]")
        _console.print("  [dim]  1=普通  2=困难  3=简单[/dim]")

        # 世代选择
        _console.print(f"\n  世代选择 (当前 {len(cfg.get('generations', []))} 代):")
        gen_labels = [
            "1代(红黄蓝绿)", "2代(金银)", "3代(红蓝绿宝石)", "4代(珍珠钻石白金)",
            "5代(黑白)", "6代(XY)", "7代(日月)", "8代(剑盾)", "9代(朱紫)",
        ]
        active_gens = set(cfg.get("generations", ALL_GENERATIONS))
        for i, (g, label) in enumerate(zip(ALL_GENERATIONS, gen_labels), 1):
            mark = "[green]✓[/green]" if g in active_gens else "[red]✗[/red]"
            _console.print(f"    {mark} {i}. {label}")

        # 猜测次数
        mg = cfg.get("max_guesses", 10)
        _console.print(f"\n  猜测次数: [yellow]{mg}[/yellow] (3-15)")

        # 显示选项
        _console.print("\n  显示选项:")
        opts = [
            ("show_more_stats", "显示更多种族值 (HP/攻击/防御/特攻/特防)"),
            ("show_more_appearance", "显示更多外形信息 (体型比较)"),
            ("show_egg_group", "显示蛋组/捕获率信息"),
            ("show_gen_arrow", "开启世代箭头提示"),
            ("reverse_order", "猜测反向显示 (最新在上)"),
            ("mischief", "小小的恶作剧 (随机干扰提示)"),
        ]
        for i, (key, label) in enumerate(opts, 1):
            mark = "[green]✓[/green]" if cfg.get(key) else "[red]✗[/red]"
            _console.print(f"    {mark} {i}. {label}  [dim](t{i} 切换)[/dim]")

        _console.print(f"\n  [cyan]a[/cyan]=全选世代  [cyan]n[/cyan]=取消全选  [cyan]s[/cyan]=保存  [cyan]q[/cyan]=取消")

        try:
            choice = _console.input("\n  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return config

        if choice == "q":
            return config
        elif choice == "s":
            try:
                save_config(cfg)
                _console.print("[green]✅ 设置已保存[/green]")
            except OSError:
                _console.print("[red]❌ 保存失败！[/red]")
            return cfg
        elif choice == "a":
            cfg["generations"] = list(ALL_GENERATIONS)
        elif choice == "n":
            cfg["generations"] = []
        elif choice in ("1", "2", "3"):
            cfg["game_mode"] = {"1": "normal", "2": "hard", "3": "easy"}[choice]
            preset = GAME_MODE_PRESETS.get(cfg["game_mode"], {})
            cfg["max_guesses"] = preset.get("default_guesses", cfg.get("max_guesses", 10))
        elif choice.isdigit() and 1 <= int(choice) <= 9:
            g = ALL_GENERATIONS[int(choice) - 1]
            gens = set(cfg.get("generations", ALL_GENERATIONS))
            if g in gens:
                gens.discard(g)
            else:
                gens.add(g)
            cfg["generations"] = list(gens)
        elif choice.startswith("t") and choice[1:].isdigit():
            idx = int(choice[1:]) - 1
            toggle_keys = [k for k, _ in opts]
            if 0 <= idx < len(toggle_keys):
                cfg[toggle_keys[idx]] = not cfg.get(toggle_keys[idx], False)


def _show_pokemon_art(name_en: str, pokemon_id: int) -> None:
    """在终端显示宝可梦精灵图（使用 term-image 渲染）"""
    show_sprite(name_en, pokemon_id)


def _show_answer(target: PokemonEntry, preamble: str, style: str) -> None:
    """统一展示答案 + 宝可梦像素画
    
    Args:
        target: 目标宝可梦
        preamble: 前置文本（已含 Rich markup）
        style: Panel 样式 (border_style, title)
    """
    console.print(Panel(
        (
            f"{preamble}\n\n"
            f"  答案: [bold]{target['name']}[/bold] ({target['name_en']}) #{target['id']:04d}"
        ),
        border_style="dim", title=style,
    ))
    _show_pokemon_art(target["name_en"], target["id"])


# ══════════════════════════════════════════════
#  核心游戏
# ══════════════════════════════════════════════

def run_game(pokemon_list: list[PokemonEntry], config: ConfigDict) -> None:
    """运行一局游戏"""
    if PromptSession is None or CompleteStyle is None:
        _console.print("[red]缺少 prompt_toolkit，无法启动交互补全。[/red]")
        return

    gen_filter = set(config.get("generations", []))
    max_guesses_raw = config.get("max_guesses", 10)
    max_guesses = max(3, min(15, int(max_guesses_raw) if isinstance(max_guesses_raw, (int, float)) else 10))

    pool = [p for p in pokemon_list if p["generation"] in gen_filter]
    total_pool_size = len(pool)
    if not pool:
        _console.print("[red]请至少选择一个世代！[/red]")
        return

    _data.QUIET = True
    target = random.choice(pool)
    target_details: PokemonEntry = cast(PokemonEntry, dict(target))
    _target_done = threading.Event()
    _target_status: str = "loading"

    def _fetch_target() -> None:
        nonlocal target_details, _target_status
        try:
            enriched = cast(PokemonEntry, get_pokemon_details(
                cast(dict[str, object], target)))
            species = cast(dict[str, object] | None,
                           fetch_species_data(target["id"]))
            if species:
                enriched["egg_groups"] = cast(list[str], species.get("egg_groups", []))
                cr = species.get("capture_rate")
                enriched["capture_rate"] = int(cr) if cr is not None else 0
            target_details = enriched
            _target_status = "done"
        except Exception:
            _target_status = "error"
        finally:
            _target_done.set()

    threading.Thread(target=_fetch_target, daemon=True).start()

    guesses_with_hints: list[GuessRecord] = []
    guessed_names: set[str] = set()
    start_time = time.time()

    # 构建快速索引 (游戏内复用，避免每次 guess 重建)
    pokemon_index: dict[object, object] = build_pokemon_index(cast(list[dict[str, object]], pokemon_list))

    # 补全会话
    completer = PokemonCompleter(pokemon_list)
    session = PromptSession(
        completer=completer,
        complete_style=CompleteStyle.MULTI_COLUMN,
        refresh_interval=0.5,
        enable_history_search=False,
    )

    _console.print(Panel(
        (
            f"[bold cyan]🎮 新游戏开始！[/bold cyan]\n\n"
            f"  宝可梦池 [bold yellow]{total_pool_size}[/bold yellow] 只\n"
            f"  最多猜测 [bold yellow]{max_guesses}[/bold yellow] 次\n"
            f"  输入宝可梦中文名/英文名/编号（支持模糊补全）\n"
            "  输入 [bold red]q[/bold red] 退出  |  [bold red]reveal[/bold red] 揭晓答案\n"
        ),
        border_style="dim", title="🎯 猜猜看",
    ))
    with _console.status("[dim]🔄 获取中...[/dim]", spinner="dots"):
        _target_done.wait(timeout=8)

    while len(guesses_with_hints) < max_guesses:
        remaining = max_guesses - len(guesses_with_hints)
        pool_remaining = compute_remaining_pool(pool, guesses_with_hints, config)
        session.message = f"\n🔮 还剩 {remaining}/{max_guesses} 次 | 🎯 剩余 {pool_remaining} 只 | 猜: "

        try:
            guess_input = session.prompt()
        except (KeyboardInterrupt, EOFError):
            _show_answer(
                target,
                "[dim]退出[/dim]",
                "👋 再见",
            )
            _safe_save_stats(False, len(guesses_with_hints))
            return

        guess_input = guess_input.strip()
        if not guess_input:
            continue

        if guess_input.lower() in ("q", "quit"):
            _show_answer(
                target,
                "[yellow]退出[/yellow]",
                "👋 再见",
            )
            _safe_save_stats(False, len(guesses_with_hints))
            return

        if guess_input.lower() == "reveal":
            _show_answer(
                target,
                "[yellow]揭晓答案[/yellow]",
                "🔍 Reveal",
            )
            _safe_save_stats(False, len(guesses_with_hints))
            return

        guess = cast(PokemonEntry | None, find_pokemon(guess_input, pokemon_list, cast(dict[object, PokemonEntry], pokemon_index)))
        if not guess:
            suggestions = cast(list[PokemonEntry], get_fuzzy_matches(guess_input, pokemon_list, limit=5))
            if suggestions:
                sug = "  ".join(f"[cyan]{s['name']}[/cyan]({s['name_en']})" for s in suggestions)
                _console.print(f"[yellow]找不到「{guess_input}」，你是不是: {sug}[/yellow]")
            else:
                _console.print(f"[yellow]找不到「{guess_input}」[/yellow]")
            continue

        # 歧义检测: 非精确匹配时检查是否有其他高分候选项
        q_norm = guess_input.strip().lower()
        guess_en = guess["name_en"].lower()
        if q_norm not in (guess["name"], guess_en, str(guess["id"]), f"#{guess['id']}"):
            alt_matches = get_fuzzy_matches(guess_input, pokemon_list, limit=3)
            others = [m for m in alt_matches if m["id"] != guess["id"]]
            if others:
                alt_names = "  ".join(f"[cyan]{m['name']}[/cyan]({m['name_en']})" for m in others[:2])
                _console.print(f"[yellow]⚠ 你是不是指: {alt_names}？已按最佳匹配选择 {guess['name']}。[/yellow]")

        if guess["name"] in guessed_names:
            _console.print(f"[yellow]已经猜过 {guess['name']} 了！[/yellow]")
            continue

        guessed_names.add(guess["name"])
        with _console.status("[dim]🔄 获取中...[/dim]", spinner="dots"):
            guess_details = cast(PokemonEntry, get_pokemon_details(
                cast(dict[str, object], guess)))
            guess_species = cast(dict[str, object] | None,
                                 fetch_species_data(guess["id"]))
        if guess_species:
            guess_details["egg_groups"] = cast(list[str], guess_species.get("egg_groups", []))
        _target_done.wait(timeout=8)
        hints = list(compare_pokemon(target_details, guess_details, config))

        # 小恶作剧模式
        if config.get("mischief") and hints:
            mischief_indices = [i for i, h in enumerate(hints)
                                if len(h) == 4 and h[2] != "exact" and h[3] is not None]
            if mischief_indices:
                idx = random.choice(mischief_indices)
                label, val, level, arrow = hints[idx]
                hints[idx] = Hint(label, val, level, "↑" if arrow == "↓" else "↓")

        guesses_with_hints.append((guess, hints))
        _console.print()
        show_hints_table(guesses_with_hints, max_guesses, config,
                         pool_size=compute_remaining_pool(pool, guesses_with_hints, config))

        if guess["id"] == target["id"]:
            elapsed = time.time() - start_time
            _show_answer(
                target,
                (
                    f"[bold green]🎉 猜对了！[/bold green]\n"
                    f"  用了 [bold yellow]{len(guesses_with_hints)}[/bold yellow] 次\n"
                    f"  耗时 [bold cyan]{elapsed:.0f}[/bold cyan] 秒"
                ),
                "🏆 You Win!",
            )
            save_game_stats(True, len(guesses_with_hints))
            return

        if len(guesses_with_hints) >= max_guesses:
            _show_answer(
                target,
                "[bold red]😢 游戏结束！[/bold red]",
                "💀 Game Over",
            )
            save_game_stats(False, len(guesses_with_hints))
            return


# ══════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════

def main() -> None:
    """程序主入口"""
    from data import load_pokemon_data

    show_logo()
    _console.print("[dim]正在加载宝可梦数据...[/dim]")
    try:
        pokemon_list = load_pokemon_data()
    except (FileNotFoundError, ValueError) as exc:
        _console.print(f"[red]错误: {exc}[/red]")
        return
    _console.print(f"[green]✅ 已加载 {len(pokemon_list)} 只宝可梦[/green]")
    pokemon_list = cast(list[PokemonEntry], pokemon_list)

    gen_counts: dict[str, int] = {}
    for p in pokemon_list:
        gen = p["generation"]
        gen_counts[gen] = gen_counts.get(gen, 0) + 1
    gen_info = "  ".join(
        f"[cyan]{GEN_MAP.get(g, (g,))[0]}[/cyan]({c})"
        for g, c in sorted(gen_counts.items(),
                           key=lambda x: GEN_MAP.get(x[0], (x[0], 0))[1])
    )
    _console.print(f"[dim]{gen_info}[/dim]")

    from constants import CACHE_DIR
    cached = 0
    if os.path.isdir(CACHE_DIR):
        cached = len([f for f in os.listdir(CACHE_DIR) if f.endswith(".json")])
    _console.print(f"[dim]PokeAPI 缓存: {cached} 个（首次猜测时自动拉取）[/dim]\n")

    config = load_config()
    if not config.get("generations"):
        config["generations"] = list(ALL_GENERATIONS)

    while True:
        _console.print("\n[bold cyan]═══ 主菜单 ═══[/bold cyan]")
        _console.print("  [bold]1[/bold]. 🎮 开始游戏")
        _console.print("  [bold]2[/bold]. 📊 查看统计")
        _console.print("  [bold]3[/bold]. ⚙️  设置")
        _console.print("  [bold]q[/bold]. 退出\n")

        try:
            choice = _console.input("[cyan]选择 > [/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            _console.print("\n[dim]再见！[/dim]")
            break

        if choice == "1":
            if not config.get("generations"):
                config["generations"] = list(ALL_GENERATIONS)
            run_game(pokemon_list, config)
        elif choice == "2":
            show_game_stats(len(pokemon_list))
        elif choice == "3":
            config = show_settings(config)
        elif choice.lower() in ("q", "quit", "exit"):
            _console.print("\n[dim]再见！捕捉更多宝可梦！[/dim] 🎉")
            break
