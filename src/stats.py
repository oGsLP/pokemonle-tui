"""
游戏统计 — 胜率/猜测次数的持久化
"""
import json
import os
import sys
from typing import Dict

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    fcntl = None  # type: ignore[assignment]
    _HAS_FCNTL = False

import constants


def _default_stats() -> dict:
    return {"wins": 0, "total": 0, "guesses_history": [], "current_streak": 0, "best_streak": 0}


def _load_stats(path: str | None = None) -> Dict:
    """加载统计文件，不存在则返回空结构"""
    if path is None:
        path = constants.STATS_FILE
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"警告: 统计文件损坏，使用默认统计: {path}", file=sys.stderr)
        except OSError as exc:
            print(f"警告: 无法读取统计文件，使用默认统计: {exc}", file=sys.stderr)
    return _default_stats()


def save_game_stats(won: bool, num_guesses: int, path: str | None = None) -> None:
    """保存一局游戏的结果（含连胜追踪）"""
    if path is None:
        path = constants.STATS_FILE

    stats = _load_stats(path)
    stats["total"] += 1
    if won:
        stats["wins"] = stats.get("wins", 0) + 1
        stats["current_streak"] = stats.get("current_streak", 0) + 1
        stats["best_streak"] = max(stats.get("best_streak", 0), stats["current_streak"])
    else:
        stats["current_streak"] = 0
    stats.setdefault("guesses_history", []).append(num_guesses)

    try:
        with open(path, "w") as f:
            if _HAS_FCNTL:
                fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(stats, f, ensure_ascii=False)
    except OSError:
        print(f"警告: 无法保存游戏统计: {path}", file=sys.stderr)
        raise


def _build_distribution(history: list[int]) -> dict[int, int]:
    dist: dict[int, int] = {}
    for g in history:
        dist[g] = dist.get(g, 0) + 1
    return dist


def get_stats_summary(pokemon_count: int) -> str:
    """返回统计摘要文本（含连胜和分布直方图）"""
    stats = _load_stats()
    total = stats["total"]
    wins = stats["wins"]
    accuracy = f"{wins / total * 100:.1f}%" if total > 0 else "N/A"
    history = stats.get("guesses_history", [])
    avg_guess = f"{sum(history) / len(history):.1f}" if history else "N/A"
    current_streak = stats.get("current_streak", 0)
    best_streak = stats.get("best_streak", 0)

    lines = [
        "🏆 游戏统计",
        "━━━━━━━━━━━━━━━━",
        f"  宝可梦池:  {pokemon_count} 只",
        f"  总场次:    {total}",
        f"  胜场:     {wins}",
        f"  胜率:     {accuracy}",
        f"  平均猜测:  {avg_guess} 次",
        f"  当前连胜:  {current_streak}",
        f"  最佳连胜:  {best_streak}",
        "",
        "📊 猜测分布",
        "━━━━━━━━━━━━━━━━",
    ]

    distribution = _build_distribution(history)
    max_count = max(distribution.values()) if distribution else 1
    for guesses in range(1, 16):
        count = distribution.get(guesses, 0)
        bar_len = int(count / max_count * 10) if max_count > 0 else 0
        bar = "█" * bar_len if bar_len > 0 else " "
        label = f"{guesses:2d}次"
        lines.append(f"  {label} {bar} {count}")

    return "\n".join(lines)
