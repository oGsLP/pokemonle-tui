# Pokemonle-TUI 深度审计报告

> 日期: 2026-05-09 | 代码量: 2,622 行 | 测试: 92 项

---

## 问题汇总 (共 76 项)

### 🚨 Bug（功能性缺陷）- 10 项

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 1 | `build_pokemon_index` 重复 ID 覆盖 | `src/data.py:54-69` | 57 个地区形态变体与原始形态共享 ID，后入者覆盖前入者，`find_pokemon("19")` 返回 Alolan 形态 |
| 2 | `reverse_order` 配置死项 | `src/game.py:209`, `src/constants.py:81` | 设置面板可切换但 `show_hints_table`/`run_game` 从未读取，无任何效果 |
| 3 | PokeAPI 7 个字段获取后未使用 | `src/data.py:145-151` | `is_legendary`, `is_mythical`, `growth_rate`, `shape`, `habitat`, `hatch_counter`, `gender_rate` 拉取缓存但从未引用 |
| 4 | `_target_status = "error"` 从未被检查 | `src/game.py:317-320` | 目标获取线程失败设状态为 error，但游戏循环从不检查，玩家使用残缺数据无感知 |
| 5 | 目标详情超时后使用残缺数据 | `src/game.py:300, 351` | `_target_done.wait(timeout=8)` 超时后 target_details 仍是浅拷贝，缺少 stat_total/speed/height/weight |
| 6 | 日文输入全角/半角不匹配 | `src/data.py:45` | `_name_jp_norm` 仅做 `lower()`，全角片假名与用户输入的半角不匹配 |
| 7 | `#` 编号前缀处理不一致 | `src/fuzzy.py:92-96` | `q.lstrip("#")` 后 `poke_id.startswith(...)` 逻辑在 `poke_id="0025"` 时误匹配 |
| 8 | `PokemonCompleter` 类在 `try/except ImportError: pass` 内定义 | `src/fuzzy.py:192-236` | 部分导入失败时类不定义，后续引用导致 NameError |
| 9 | `fcntl` 在 Windows 上不可用 | `src/stats.py:4` | `fcntl.flock` 是 POSIX 专有，Windows 上崩溃 |
| 10 | `Pillow` 不在 `requirements.txt` 中 | `requirements.txt` | `ascii_art.py` 导入 PIL 但 `requirements.txt` 未列出 |

### ⚙️ 性能问题 - 5 项

| # | 问题 | 位置 |
|---|------|------|
| 11 | `PokemonTrie._collect_ids` 用 `list.pop(0)` 实现 BFS (O(n²)) | `src/fuzzy.py:73` |
| 12 | `compute_remaining_pool` 每回合调用两次 (每次约 130K 次 hint 计算) | `src/comparison.py:162`, `src/game.py:355,438` |
| 13 | `fetch_species_data` 每次猜测都调用，即使 `show_egg_group=False` | `src/game.py:419-420` |
| 14 | 精灵图下载同步阻塞主线程 | `src/ascii_art.py:49-78` |
| 15 | `_name_jp_norm` 计算了却未用于索引 | `src/data.py:45, 63-67` |

### 🧪 测试覆盖缺失 - 17 项

| # | 问题 | 位置 |
|---|------|------|
| 16 | `compute_remaining_pool` 零测试 | `src/comparison.py:162` |
| 17 | `format_share_result` 零测试 | `src/share.py:4` |
| 18 | `PokemonTrie` 类零测试 (4 方法) | `src/fuzzy.py:21-81` |
| 19 | `PokemonCompleter` 零测试 | `src/fuzzy.py:196-236` |
| 20 | `show_settings` 零测试 | `src/game.py:166` |
| 21 | `show_hints_table` 零测试 | `src/game.py:102` |
| 22 | `show_logo` 零测试 | `src/game.py:61` |
| 23 | `show_game_stats` 零测试 | `src/game.py:157` |
| 24 | `_build_distribution` 零测试 | `src/stats.py:63` |
| 25 | `_show_answer` 零测试 | `src/game.py:260` |
| 26 | `_show_pokemon_art` 零测试 | `src/game.py:255` |
| 27 | `_safe_save_stats` 零测试 | `src/game.py:53` |
| 28 | `main` 零测试 | `src/game.py:482` |
| 29 | `_cached_or_fetch` 无直接单元测试 | `src/data.py:72` |
| 30 | `_download_sprite` 无测试 | `src/ascii_art.py:49` |
| 31 | 无真实集成测试 | `tests/test_all.py:818-890` |
| 32 | 缺失边缘情况测试 (6 个场景) | 详见报告 |

### 💀 死代码 - 9 项

| # | 问题 | 位置 |
|---|------|------|
| 33-39 | PokeAPI 7 个未使用字段 | `src/data.py:145-151` |
| 40 | `_name_jp_norm` 未被 `build_pokemon_index` 使用 | `src/data.py:45, 63-67` |
| 41 | `PokemonData` 别名与 `PokemonEntry` 完全相同，无价值 | `src/poketypes.py:60` |

### 🎮 游戏逻辑缺陷 - 4 项

| # | 问题 | 位置 |
|---|------|------|
| 42 | 体型判断阈值过于粗糙 (1.5x/0.67x) | `src/comparison.py:148-157` |
| 43 | 速度属性 hard 模式 ±8 过于严格 | `src/constants.py:70` |
| 44 | 编号范围提示暗示难度相似但编号差距 ≠ 难度相似 | `src/comparison.py:47-53` |
| 45 | 蛋组数据缺失时不优雅降级 | `src/comparison.py:66-81` |

### 🖥️ UX 缺陷 - 9 项

| # | 问题 | 位置 |
|---|------|------|
| 46 | 无法撤销猜测 | `src/game.py:353-438` |
| 47 | 无单项提示功能 | `src/game.py:353-389` |
| 48 | 无法查看剩余候选池宝可梦列表 | `src/game.py:355` |
| 49 | 游戏结束后无"再来一局"选项 | `src/game.py:440-475` |
| 50 | 设置面板仅支持数字输入 | `src/game.py:218-219` |
| 51 | 无每日挑战模式 | — |
| 52 | 无游戏状态保存/恢复 | — |
| 53 | 无键盘快捷键导航主菜单 | `src/game.py:517-539` |
| 54 | species 数据无条件拉取即使蛋组未启用 | `src/game.py:419-422` |

### ♿ 可访问性缺陷 - 3 项

| # | 问题 | 位置 |
|---|------|------|
| 55 | miss/far 同用 dim 样式，部分终端不可见 | `src/game.py:43-44` |
| 56 | 颜色是唯一提示级别标识，无文本/图标替代 | `src/game.py:41-46` |
| 57 | 精灵图无文本回退 | `src/ascii_art.py:138-145` |

### 🏗️ 架构问题 - 10 项

| # | 问题 | 位置 |
|---|------|------|
| 58 | `game.py` 上帝模块 (540 行) | `src/game.py` |
| 59 | `constants.py` 混合路径/游戏数据/配置 | `src/constants.py` |
| 60 | `sys.path.insert` hack 作为导入机制 | `pokemonle.py:10` |
| 61 | `data.QUIET` 全局可变状态 | `src/data.py:15` |
| 62 | `_console = Console()` 模块级单例 | `src/game.py:38` |
| 63 | `_cache: dict` 无线程安全 | `src/ascii_art.py:36` |
| 64 | `compute_remaining_pool` 职责归属错误 | `src/comparison.py:162` |
| 65 | 43 处 `cast()` 调用 | 多处 |
| 66 | `__init__.py` 为空 | `src/__init__.py` |
| 67 | `_config_file()` / `_stats_file()` 测试反模式 | `src/config.py:14`, `src/stats.py:13` |

### 📊 统计/数据缺陷 - 4 项

| # | 问题 | 位置 |
|---|------|------|
| 68 | 统计数据不区分难度模式 | `src/stats.py:18-19` |
| 69 | `guesses_history` 无限增长无归档 | `src/stats.py:18` |
| 70 | `save_game_stats` 语义混乱 (a+ → seek(0) → truncate → 写入) | `src/stats.py:40-57` |
| 71 | `_load_stats` 重复调用加载文件到内存再重写 | `src/stats.py:40-57` |

### 🔗 依赖风险 - 5 项

| # | 问题 | 位置 |
|---|------|------|
| 72 | PokeAPI JSON 结构变更风险 | `src/data.py:125-131,141-152` |
| 73 | `term-image` API 变更风险 | `src/ascii_art.py:156-165` |
| 74 | `prompt_toolkit` API 变更风险 | `src/fuzzy.py:196-236` |
| 75 | `rich` API 变更风险 | `src/game.py` (全文) |
| 76 | `pokemon_full_list.json` 结构隐式依赖 | `src/data.py:33-50` |
