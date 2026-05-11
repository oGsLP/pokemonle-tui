"""UI 渲染模块 — logo、表格、设置面板、答案展示"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.align import Align

from .constants import ALL_GENERATIONS, GAME_MODE_PRESETS, TYPE_COLORS, TYPE_CN_TO_EN_MAP
from .poketypes import ConfigDict, GuessRecord, PokemonEntry
from .config import save_config
from .stats import get_stats_summary
from .ascii_art import show_sprite

_console = Console()

HINT_TAIL = {"exact": " ✓", "partial": "", "close": "", "miss": "", "far": ""}
HINT_COLOR = {"exact": "bold green", "partial": "bold yellow", "close": "bold yellow",
              "miss": "dim", "far": "dim"}
ARROW_UP = "bold green"
ARROW_DOWN = "bold red"


def _hint_color(level: str) -> str:
    return HINT_COLOR.get(level, "white")


def _hint_symbol(level: str) -> str:
    if level == "exact":
        return "●"
    if level in {"partial", "close"}:
        return "◐"
    return "○"


def show_logo() -> None:
    logo = r"""
  ██████╗ ██╗   ██╗ █████╗  ██████╗██╗  ██╗██╗     ███████╗███████╗
  ██╔══██╗██║   ██║██╔══██╗██╔════╝██║ ██╔╝██║     ██╔════╝██╔════╝
  ██████╔╝██║   ██║███████║██║     █████╔╝ ██║     █████╗  ███████╗
  ██╔═══╝ ██║   ██║██╔══██║██║     ██╔═██╗ ██║     ██╔══╝  ╚════██║
  ██║     ╚██████╔╝██║  ██║╚██████╗██║  ██╗███████╗███████╗███████║
  ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
  ── 宝可梦猜猜猜 CLI 0.2.2 ──
"""
    _console.print(Panel(
        Align.center(Text(logo, style="bold cyan")),
        border_style="dim", box=box.ROUNDED, padding=(0, 1),
    ))


def _format_hint(label: str, val: str, level: str, extra: str = "") -> Text:
    color = _hint_color(level)
    t = Text(style=color)
    _ = t.append(f"{_hint_symbol(level)} ", style=color)
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
        expand=False,
    )
    table.add_column("#", style="dim", width=3, justify="right")
    table.add_column("中文名", style="bold", width=10, overflow="fold")
    table.add_column("英文名", style="dim", width=14, overflow="fold")
    for k in header_keys:
        table.add_column(k, justify="center")

    rows = list(reversed(guesses_with_hints)) if config.get("reverse_order") else guesses_with_hints

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
    _console.print(Panel(get_stats_summary(pokemon_count).strip(), border_style="dim", title="📊 Stats"))


def show_settings(config: ConfigDict) -> ConfigDict:
    cfg = dict(config)

    if not cfg.get("generations"):
        cfg["generations"] = list(ALL_GENERATIONS)

    while True:
        _console.print(f"\n{'═' * 40}")
        _console.print("  ⚙️  设置")
        _console.print("═" * 40)

        mode_display = {
            "normal": "普通模式 · 标准难度",
            "hard": "困难模式 · 更严格的提示范围和更少猜测次数",
            "easy": "简单模式 · 更宽松的提示范围和更多猜测次数",
        }.get(cfg.get("game_mode", "normal"), cfg.get("game_mode", "normal"))
        _console.print(f"\n  游戏模式: [yellow]{mode_display}[/yellow]")
        _console.print("  [dim]  1=普通  2=困难  3=简单  (e=简单 h=困难)[/dim]")

        _console.print(f"\n  世代选择 (当前 {len(cfg.get('generations', []))} 代):")
        gen_labels = [
            "1代(红黄蓝绿)", "2代(金银)", "3代(红蓝绿宝石)", "4代(珍珠钻石白金)",
            "5代(黑白)", "6代(XY)", "7代(日月)", "8代(剑盾)", "9代(朱紫)",
        ]
        active_gens = set(cfg.get("generations", ALL_GENERATIONS))
        for i, (g, label) in enumerate(zip(ALL_GENERATIONS, gen_labels), 1):
            mark = "[green]✓[/green]" if g in active_gens else "[red]✗[/red]"
            _console.print(f"    {mark} {i}. {label}")

        mg = cfg.get("max_guesses", 10)
        _console.print(f"\n  猜测次数: [yellow]{mg}[/yellow] (3-15)")

        _console.print("\n  显示选项:")
        opts = [
            ("show_more_stats", "显示更多种族值 (HP/攻击/防御/特攻/特防)", "m"),
            ("show_more_appearance", "显示更多外形信息 (体型比较)", "p"),
            ("show_egg_group", "显示蛋组信息", "g"),
            ("show_gen_arrow", "开启世代箭头提示", "r"),
            ("reverse_order", "猜测反向显示 (最新在上)", "o"),
            ("mischief", "小小的恶作剧 (随机干扰提示)", "i"),
        ]
        for i, (key, label, shortcut) in enumerate(opts, 1):
            mark = "[green]✓[/green]" if cfg.get(key) else "[red]✗[/red]"
            _console.print(f"    {mark} {i}. {label}  [dim]({shortcut} 切换)[/dim]")

        _console.print(f"\n  [cyan]a[/cyan]=全选世代  [cyan]n[/cyan]=重置为全部世代  [cyan]s[/cyan]=保存  [cyan]q[/cyan]=取消")

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
            cfg["generations"] = list(ALL_GENERATIONS)
        elif choice in ("1", "2", "3"):
            cfg["game_mode"] = {"1": "normal", "2": "hard", "3": "easy"}[choice]
            preset = GAME_MODE_PRESETS.get(cfg["game_mode"], {})
            cfg["max_guesses"] = preset.get("default_guesses", cfg.get("max_guesses", 10))
        elif choice == "e":
            cfg["game_mode"] = "easy"
            preset = GAME_MODE_PRESETS["easy"]
            cfg["max_guesses"] = preset.get("default_guesses", cfg.get("max_guesses", 10))
        elif choice == "h":
            cfg["game_mode"] = "hard"
            preset = GAME_MODE_PRESETS["hard"]
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
            if 0 <= idx < len(opts):
                cfg[opts[idx][0]] = not cfg.get(opts[idx][0], False)
        elif choice in ("m", "p", "g", "r", "o", "i"):
            shortcut_map = {s: k for k, _, s in opts}
            key = shortcut_map.get(choice)
            if key:
                cfg[key] = not cfg.get(key, False)


def _show_pokemon_art(name_en: str, pokemon_id: int) -> bool:
    return show_sprite(name_en, pokemon_id, console=_console)


def _show_answer(target: PokemonEntry, preamble: str, style: str) -> None:
    _console.print(Panel(
        (
            f"{preamble}\n\n"
            f"  答案: [bold]{target['name']}[/bold] ({target['name_en']}) #{target['id']:04d}"
        ),
        border_style="dim", title=style,
    ))
    shown_art = _show_pokemon_art(target["name_en"], target["id"])
    if not shown_art:
        _console.print(f"[dim]图片暂不可用：#{target['id']} {target['name_en']}[/dim]")
