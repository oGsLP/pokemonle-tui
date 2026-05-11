"""
游戏逻辑 — 核心游戏循环、主菜单入口
"""
from __future__ import annotations

import os
import random
import threading
import time

from rich.panel import Panel

from .constants import ALL_GENERATIONS, GEN_MAP, Hint
from .poketypes import ConfigDict, GuessRecord, HintRecord, PokemonEntry
from .data import get_pokemon_details, fetch_species_data, build_pokemon_index
from .config import load_config
from .comparison import compare_pokemon, compute_remaining_pool
from .fuzzy import find_pokemon, get_fuzzy_matches, PokemonCompleter
from .stats import save_game_stats
from .share import format_share_result
from .ui import show_hints_table, show_logo, show_game_stats, show_settings, _show_answer
from . import ui as _ui

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.shortcuts import CompleteStyle
except ImportError:
    PromptSession = None
    CompleteStyle = None


_console = _ui._console


class _TargetDetailsPreloader:
    def __init__(self, target: PokemonEntry) -> None:
        self.details: PokemonEntry = target
        self.status: str = "loading"
        self.error: str = ""
        self.done: threading.Event = threading.Event()
        self._timed_out: bool = False

    def fetch(self) -> None:
        try:
            enriched = get_pokemon_details(self.details, quiet=True)
            species = fetch_species_data(self.details["id"], quiet=True)
            if species:
                egg_groups = species.get("egg_groups", [])
                if isinstance(egg_groups, list):
                    enriched["egg_groups"] = [str(group) for group in egg_groups]
                cr = species.get("capture_rate")
                enriched["capture_rate"] = int(cr) if cr is not None else 0
            if not self._timed_out:
                self.details = enriched
                self.status = "done"
        except Exception as exc:
            if not self._timed_out:
                self.status = "error"
                self.error = str(exc)
        finally:
            self.done.set()

    def start(self) -> threading.Thread:
        thread = threading.Thread(target=self.fetch, daemon=True)
        thread.start()
        return thread

    def wait(self, timeout: float) -> bool:
        completed = self.done.wait(timeout=timeout)
        if not completed:
            self.mark_timed_out()
        return completed

    def mark_timed_out(self) -> None:
        if self.status == "loading":
            self.status = "timeout"
        self._timed_out = True


def _safe_save_stats(won: bool, guesses: int) -> None:
    try:
        save_game_stats(won, guesses)
    except OSError:
        pass


# ══════════════════════════════════════════════
#  核心游戏
# ══════════════════════════════════════════════

def _format_remaining_pool_warning(pool_size: int) -> str:
    if pool_size != 0:
        return ""
    return "⚠ 没有候选宝可梦完全匹配当前提示，可能是网络数据、设置项或谜题约束导致。"


def run_game(pokemon_list: list[PokemonEntry], config: ConfigDict) -> None:
    """运行一局游戏"""
    if PromptSession is None or CompleteStyle is None:
        _console.print("[red]缺少 prompt_toolkit，无法启动交互补全。[/red]")
        return

    generations = config.get("generations", [])
    gen_filter = set(generations) if isinstance(generations, list) else set()
    max_guesses_raw = config.get("max_guesses", 10)
    max_guesses = max(3, min(15, int(max_guesses_raw) if isinstance(max_guesses_raw, (int, float)) else 10))

    pool = [p for p in pokemon_list if p["generation"] in gen_filter]
    total_pool_size = len(pool)
    if not pool:
        _console.print("[red]请至少选择一个世代！[/red]")
        return

    target = random.choice(pool)
    target_preloader = _TargetDetailsPreloader(target)
    _ = target_preloader.start()

    guesses_with_hints: list[GuessRecord] = []
    guessed_names: set[str] = set()
    start_time = time.time()

    pokemon_index = build_pokemon_index(pokemon_list)

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
        _ = target_preloader.wait(timeout=8)
    if target_preloader.status == "error":
        _console.print(f"[yellow]⚠ 获取目标宝可梦详情失败，提示可能不完整[/yellow]")
    elif target_preloader.status == "timeout":
        _console.print(f"[yellow]⚠ 目标宝可梦详情加载超时，提示可能不完整[/yellow]")

    _cached_pool_remaining: int = len(pool)

    while len(guesses_with_hints) < max_guesses:
        remaining = max_guesses - len(guesses_with_hints)
        session.message = f"\n🔮 还剩 {remaining}/{max_guesses} 次 | 🎯 剩余 {_cached_pool_remaining} 只 | q=退出 reveal=看答案 | 猜: "

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

        guess = find_pokemon(guess_input, pokemon_list, pokemon_index)
        if not guess:
            suggestions = get_fuzzy_matches(guess_input, pokemon_list, limit=5)
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
            guess_details = get_pokemon_details(guess, quiet=True)
        if config.get("show_egg_group"):
            guess_species = fetch_species_data(guess["id"], quiet=True)
            if guess_species:
                egg_groups = guess_species.get("egg_groups", [])
                if isinstance(egg_groups, list):
                    guess_details["egg_groups"] = [str(group) for group in egg_groups]
        _ = target_preloader.wait(timeout=8)
        hints: list[HintRecord] = list(compare_pokemon(target_preloader.details, guess_details, config))

        # 小恶作剧模式
        if config.get("mischief") and hints:
            mischief_indices = [i for i, h in enumerate(hints)
                                if len(h) == 4 and h[2] != "exact" and h[3] is not None]
            if mischief_indices:
                idx = random.choice(mischief_indices)
                match hints[idx]:
                    case (label, val, level, arrow):
                        hints[idx] = Hint(label, val, level, "↑" if arrow == "↓" else "↓")

        guesses_with_hints.append((guess, hints))
        _cached_pool_remaining = compute_remaining_pool(pool, guesses_with_hints, config)
        warning = _format_remaining_pool_warning(_cached_pool_remaining)
        if warning:
            _console.print(f"[yellow]{warning}[/yellow]")
        _console.print()
        show_hints_table(guesses_with_hints, max_guesses, config,
                         pool_size=_cached_pool_remaining)

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
            gen_short = GEN_MAP.get(target["generation"], ("", 0))[0]
            share_text = format_share_result(
                guesses_with_hints, max_guesses,
                target["name"], target["name_en"], target["id"],
                won=True, generation_label=gen_short,
            )
            _console.print(Panel(share_text, border_style="dim", title="📋 分享结果"))
            _safe_save_stats(True, len(guesses_with_hints))
            return

        if len(guesses_with_hints) >= max_guesses:
            _show_answer(
                target,
                "[bold red]😢 游戏结束！[/bold red]",
                "💀 Game Over",
            )
            gen_short = GEN_MAP.get(target["generation"], ("", 0))[0]
            share_text = format_share_result(
                guesses_with_hints, max_guesses,
                target["name"], target["name_en"], target["id"],
                won=False, generation_label=gen_short,
            )
            _console.print(Panel(share_text, border_style="dim", title="📋 分享结果"))
            _safe_save_stats(False, len(guesses_with_hints))
            return


# ══════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════

def main() -> None:
    """程序主入口"""
    from .data import load_pokemon_data

    show_logo()
    _console.print("[dim]正在加载宝可梦数据...[/dim]")
    try:
        pokemon_list = load_pokemon_data()
    except (FileNotFoundError, ValueError) as exc:
        _console.print(f"[red]错误: {exc}[/red]")
        return
    _console.print(f"[green]✅ 已加载 {len(pokemon_list)} 只宝可梦[/green]")

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

    from .constants import CACHE_DIR
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
