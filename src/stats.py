"""
游戏统计 — 胜率/猜测次数的持久化
"""
import fcntl
import json
import os
import sys
from typing import Dict

import constants


def _stats_file() -> str:
    """动态读取统计文件路径（方便测试时替换）"""
    return constants.STATS_FILE


def _load_stats() -> Dict:
    """加载统计文件，不存在则返回空结构"""
    path = _stats_file()
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"警告: 统计文件损坏，使用默认统计: {path}", file=sys.stderr)
        except OSError as exc:
            print(f"警告: 无法读取统计文件，使用默认统计: {exc}", file=sys.stderr)
    return {"wins": 0, "total": 0, "guesses_history": []}


def save_game_stats(won: bool, num_guesses: int) -> None:
    """保存一局游戏的结果"""
    path = _stats_file()
    try:
        with open(path, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                stats = json.load(f) if os.path.getsize(path) > 0 else {"wins": 0, "total": 0, "guesses_history": []}
            except json.JSONDecodeError:
                stats = {"wins": 0, "total": 0, "guesses_history": []}
            stats["total"] += 1
            if won:
                stats["wins"] += 1
            stats["guesses_history"].append(num_guesses)
            f.seek(0)
            f.truncate()
            json.dump(stats, f, ensure_ascii=False)
    except OSError:
        print(f"警告: 无法保存游戏统计: {path}", file=sys.stderr)
        raise


def get_stats_summary(pokemon_count: int) -> str:
    """返回统计摘要文本"""
    stats = _load_stats()
    total = stats["total"]
    wins = stats["wins"]
    accuracy = f"{wins / total * 100:.1f}%" if total > 0 else "N/A"
    history = stats["guesses_history"]
    avg_guess = f"{sum(history) / len(history):.1f}" if history else "N/A"

    return f"""
🏆 游戏统计
━━━━━━━━━━━━━━━━
  宝可梦池:  {pokemon_count} 只
  总场次:    {total}
  胜场:     {wins}
  胜率:     {accuracy}
  平均猜测:  {avg_guess} 次
"""
