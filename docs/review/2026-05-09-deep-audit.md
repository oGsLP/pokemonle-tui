# Pokemonle-TUI 深度审计报告

> 日期: 2026-05-09 | 代码量: 2,622 行 | 测试: 92 → **109** 项
>
> 进度: **15/76 已完成** (20%) | Bug 全部修复 | 性能主要瓶颈已解决

---

## 完成状态图例
- ✅ 已修复
- ⬜ 待处理
- ⚠ 部分修复

---

## 🚨 Bug（功能性缺陷）- 10/10 ✅

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 1 | ✅ | `build_pokemon_index` 重复 ID 覆盖 | `src/data.py:54-69` |
| 2 | ✅ | `reverse_order` 配置死项 | `src/game.py:209`, `src/constants.py:81` |
| 3 | ✅ | PokeAPI 7 个字段获取后未使用 | `src/data.py:145-151` |
| 4 | ✅ | `_target_status = "error"` 从未被检查 | `src/game.py:317-320` |
| 5 | ✅ | 目标详情超时后使用残缺数据 | `src/game.py:300, 351` |
| 6 | ✅ | 日文输入全角/半角不匹配 | `src/data.py:45` |
| 7 | ✅ | `#` 编号前缀处理不一致 | `src/fuzzy.py:92-96` |
| 8 | ✅ | `PokemonCompleter` 类在 `try/except` 内定义 | `src/fuzzy.py:192-236` |
| 9 | ✅ | `fcntl` 在 Windows 上不可用 | `src/stats.py:4` |
| 10 | ✅ | `Pillow` 不在 `requirements.txt` 中 | `requirements.txt` |

---

## ⚙️ 性能问题 - 4/5 ✅

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 11 | ✅ | `PokemonTrie._collect_ids` 用 `list.pop(0)` (O(n²)) | `src/fuzzy.py:73` |
| 12 | ✅ | `compute_remaining_pool` 每回合调用两次 | `src/comparison.py:162`, `src/game.py:355,438` |
| 13 | ✅ | `fetch_species_data` 每次猜测都调用 | `src/game.py:419-420` |
| 14 | ⬜ | 精灵图下载同步阻塞主线程 | `src/ascii_art.py:49-78` |
| 15 | ✅ | `_name_jp_norm` 计算了却未用于索引 | `src/data.py:45, 63-67` |

---

## 🧪 测试覆盖缺失 - 3/17 ⚠

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 16 | ✅ | `compute_remaining_pool` 零测试 | `src/comparison.py:162` |
| 17 | ✅ | `format_share_result` 零测试 | `src/share.py:4` |
| 18 | ✅ | `PokemonTrie` 类零测试 (4 方法) | `src/fuzzy.py:21-81` |
| 19 | ⬜ | `PokemonCompleter` 零测试 | `src/fuzzy.py:196-236` |
| 20 | ⬜ | `show_settings` 零测试 | `src/game.py:166` |
| 21 | ⬜ | `show_hints_table` 零测试 | `src/game.py:102` |
| 22 | ⬜ | `show_logo` 零测试 | `src/game.py:61` |
| 23 | ⬜ | `show_game_stats` 零测试 | `src/game.py:157` |
| 24 | ⬜ | `_build_distribution` 零测试 | `src/stats.py:63` |
| 25 | ⬜ | `_show_answer` 零测试 | `src/game.py:260` |
| 26 | ⬜ | `_show_pokemon_art` 零测试 | `src/game.py:255` |
| 27 | ⬜ | `_safe_save_stats` 零测试 | `src/game.py:53` |
| 28 | ⬜ | `main` 零测试 | `src/game.py:482` |
| 29 | ⬜ | `_cached_or_fetch` 无直接单元测试 | `src/data.py:72` |
| 30 | ⬜ | `_download_sprite` 无测试 | `src/ascii_art.py:49` |
| 31 | ⬜ | 无真实集成测试 | `tests/test_all.py:818-890` |
| 32 | ⬜ | 缺失边缘情况测试 (6 个场景) | 详见报告 |

---

## 💀 死代码 - 8/9 ⚠

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 33-39 | ✅ | PokeAPI 7 个未使用字段 (已移除) | `src/data.py:145-151` |
| 40 | ✅ | `_name_jp_norm` 未被 `build_pokemon_index` 使用 (已修复) | `src/data.py:45, 63-67` |
| 41 | ⬜ | `PokemonData` 别名与 `PokemonEntry` 完全相同 | `src/poketypes.py:60` |

---

## 🎮 游戏逻辑缺陷 - 0/4 ⬜

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 42 | ⬜ | 体型判断阈值过于粗糙 (1.5x/0.67x) | `src/comparison.py:148-157` |
| 43 | ⬜ | 速度属性 hard 模式 ±8 过于严格 | `src/constants.py:70` |
| 44 | ⬜ | 编号差距 ≠ 难度相似 | `src/comparison.py:47-53` |
| 45 | ⬜ | 蛋组数据缺失时不优雅降级 | `src/comparison.py:66-81` |

---

## 🖥️ UX 缺陷 - 1/9 ⚠

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 46 | ⬜ | 无法撤销猜测 | `src/game.py:353-438` |
| 47 | ⬜ | 无单项提示功能 | `src/game.py:353-389` |
| 48 | ⬜ | 无法查看剩余候选池宝可梦列表 | `src/game.py:355` |
| 49 | ⬜ | 游戏结束后无"再来一局"选项 | `src/game.py:440-475` |
| 50 | ⬜ | 设置面板仅支持数字输入 | `src/game.py:218-219` |
| 51 | ⬜ | 无每日挑战模式 | — |
| 52 | ⬜ | 无游戏状态保存/恢复 | — |
| 53 | ⬜ | 无键盘快捷键导航主菜单 | `src/game.py:517-539` |
| 54 | ✅ | species 数据无条件拉取 (已按配置跳过) | `src/game.py:419-422` |

---

## ♿ 可访问性缺陷 - 0/3 ⬜

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 55 | ⬜ | miss/far 同用 dim 样式，部分终端不可见 | `src/game.py:43-44` |
| 56 | ⬜ | 颜色是唯一提示级别标识 | `src/game.py:41-46` |
| 57 | ⬜ | 精灵图无文本回退 | `src/ascii_art.py:138-145` |

---

## 🏗️ 架构问题 - 0/10 ⬜

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 58 | ⬜ | `game.py` 上帝模块 (540 行) | `src/game.py` |
| 59 | ⬜ | `constants.py` 混合路径/游戏数据/配置 | `src/constants.py` |
| 60 | ⬜ | `sys.path.insert` hack 导入机制 | `pokemonle.py:10` |
| 61 | ⬜ | `data.QUIET` 全局可变状态 | `src/data.py:15` |
| 62 | ⬜ | `_console = Console()` 模块级单例 | `src/game.py:38` |
| 63 | ⬜ | `_cache: dict` 无线程安全 | `src/ascii_art.py:36` |
| 64 | ⬜ | `compute_remaining_pool` 职责归属错误 | `src/comparison.py:162` |
| 65 | ⬜ | 43 处 `cast()` 调用 | 多处 |
| 66 | ⬜ | `__init__.py` 为空 | `src/__init__.py` |
| 67 | ⬜ | `_config_file()` / `_stats_file()` 测试反模式 | `src/config.py:14`, `src/stats.py:13` |

---

## 📊 统计/数据缺陷 - 0/4 ⬜

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 68 | ⬜ | 统计数据不区分难度模式 | `src/stats.py:18-19` |
| 69 | ⬜ | `guesses_history` 无限增长无归档 | `src/stats.py:18` |
| 70 | ⬜ | `save_game_stats` 语义混乱 (a+ → seek → truncate) | `src/stats.py:40-57` |
| 71 | ⬜ | `_load_stats` 重复加载文件到内存再重写 | `src/stats.py:40-57` |

---

## 🔗 依赖风险 - 0/5 ⬜

| # | 状态 | 问题 | 位置 |
|---|------|------|------|
| 72 | ⬜ | PokeAPI JSON 结构变更风险 | `src/data.py:125-131,141-152` |
| 73 | ⬜ | `term-image` API 变更风险 | `src/ascii_art.py:156-165` |
| 74 | ⬜ | `prompt_toolkit` API 变更风险 | `src/fuzzy.py:196-236` |
| 75 | ⬜ | `rich` API 变更风险 | `src/game.py` (全文) |
| 76 | ⬜ | `pokemon_full_list.json` 结构隐式依赖 | `src/data.py:33-50` |

---

## 📈 待完成汇总 (61 项)

### 按优先级分组

**🟡 下一批 (低风险/高价值) — 24 项**
- **性能** #14: 精灵图异步下载
- **测试** #19-32: 14 个函数/类零测试 + 集成测试 + 边缘情况测试
- **游戏逻辑** #42-45: 阈值调整、蛋组降级
- **统计** #68-71: 按模式区分统计、history 归档、文件 I/O 清理

**🟠 中等 (需设计/重构) — 19 项**
- **UX** #46-53: 撤销、提示功能、候选池查看、再来一局等
- **可访问性** #55-57: dim→文本、颜色+图标、精灵图回退

**🔴 结构 (大规模重构) — 18 项**
- **架构** #58-67: 拆分 game.py、清理 constants.py、移除 sys.path hack、去 cast
- **死代码** #41: 移除 PokemonData 别名
- **依赖** #72-76: 响应验证、版本锁定、JSON schema

### 建议执行顺序

1. **本周可做**: #14 (精灵图异步), #42-45 (游戏平衡微调), #19 (PokemonCompleter 测试), #68-71 (统计清理)
2. **本月目标**: #46-53 (UX 改善), #55-57 (可访问性), #24-32 (测试补齐)
3. **下个版本**: #58-67 (架构重构), #72-76 (依赖加固)
