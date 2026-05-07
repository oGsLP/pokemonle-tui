#!/usr/bin/env python3
"""
Pokemonle CLI v2 — 宝可梦猜猜猜 终端版
基于 https://github.com/QuantAskk/pokemonle 的数据和玩法
"""
import os
import sys

# 确保 src/ 在 import 路径里
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from game import main

if __name__ == "__main__":
    main()
