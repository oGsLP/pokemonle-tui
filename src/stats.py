"""
游戏统计 — 胜率/猜测次数的持久化
"""
import json
import os
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
        except Exception:
            pass
    return {"wins": 0, "total": 0, "guesses_history": []}


def save_game_stats(won: bool, num_guesses: int) -> None:
    """保存一局游戏的结果"""
    stats = _load_stats()
    stats["total"] += 1
    if won:
        stats["wins"] += 1
    stats["guesses_history"].append(num_guesses)
    with open(_stats_file(), "w") as f:
        json.dump(stats, f, ensure_ascii=False)


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
