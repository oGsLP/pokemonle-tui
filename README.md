# Pokemonle TUI — 宝可梦猜猜猜 终端版

Rich 终端 Wordle 风格宝可梦猜谜游戏，基于 [QuantAskk/pokemonle](https://github.com/QuantAskk/pokemonle) 的数据和玩法移植。

## 功能

- 🎮 **Wordle 玩法** — 多维度提示（编号/属性/世代/种族值/身高/体重/蛋组）
- 🌏 **多语言输入** — 中文名、英文名、日文名、编号均可，`prompt_toolkit` 模糊补全
- ⚙️ **三种难度** — 简单/普通/困难，影响提示容差和猜测次数
- 🎨 **Rich TUI** — 彩色表格、属性色标、emoji 图标
- 📊 **游戏统计** — 胜率、平均猜测次数持久化
- 🗂️ **世代筛选** — 1-9 世代自由组合
- 🔥 **PokeAPI 集成** — 种族值、蛋组等详细数据懒加载 + 本地缓存

## 安装

```bash
git clone https://github.com/oGsLP/pokemonle-tui.git
cd pokemonle-tui
pip install rich prompt_toolkit
```

## 运行

```bash
python3 pokemonle.py
```

## 操作

| 按键 | 功能 |
|------|------|
| 输入宝可梦名 | 进行猜测 |
| `3` → 设置 | 切换世代/难度/显示选项 |
| `2` | 查看胜率统计 |
| `q` / `quit` | 退出游戏 |
| `reveal` | 揭晓答案 |

## 设置选项

- **显示更多种族值** — HP/攻击/防御/特攻/特防
- **显示更多外形** — 体型比较
- **显示蛋组** — 蛋组/捕获率提示
- **世代箭头** — ↑↓ 世代方向提示
- **反向显示** — 最新猜测在上
- **恶作剧模式** — 随机干扰提示方向

## 运行测试

```bash
python3 -m pytest tests/ -v
```

## 鸣谢

- 原始项目 **[QuantAskk/pokemonle](https://github.com/QuantAskk/pokemonle)** — 宝可梦数据与核心玩法设计
- **[PokeAPI](https://pokeapi.co/)** — 宝可梦详细数据

## 许可

本项目为个人学习用途，宝可梦数据版权归原项目及任天堂/Game Freak 所有。
