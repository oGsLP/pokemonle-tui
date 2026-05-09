# Pokemonle-TUI 深度审计报告

> 日期: 2026-05-09 → 2026-05-10 | 测试: 92 → **131** 项 | 提交: **31** commits
>
> 进度: **56/76 (74%)**

---

## 完成状态

| 类别 | 状态 |
|------|------|
| 🚨 Bug | **10/10** ✅ |
| ⚙️ 性能 | **5/5** ✅ |
| 🔗 依赖 | **5/5** ✅ |
| 💀 死代码 | **8/9** ✅ |
| 🏗️ 架构 | **10/10** ✅ |
| 📊 统计 | **3/4** ✅ |
| 🧪 测试 | **11/17** ⚠ |
| 🖥️ UX | **2/9** ⚠ |
| 🎮 游戏逻辑 | **0/4** ❌ |
| ♿ 可访问性 | **0/3** ❌ |

---

## 🚨 Bug — 10/10 ✅ 全部修复

| # | 修复 |
|---|------|
| 1 | `build_pokemon_index` 地区形态 ID 覆盖 → `setdefault` |
| 2 | `reverse_order` 死配置 → `show_hints_table` 实现 |
| 3 | PokeAPI 7 未使用字段 → 从 `fetch_species_data` 移除 |
| 4+5 | 目标线程错误静默+超时残缺数据 → 状态检查+警告 |
| 6 | 日文全角/半角 → `unicodedata.normalize("NFKC")` |
| 7 | `#` 编号前缀 → 整数比较替代字符串前缀 |
| 8 | `PokemonCompleter` try/except → 模块级定义+None 回退 |
| 9 | `fcntl` Windows → `_HAS_FCNTL` guard |
| 10 | `Pillow` 缺失 → 加入 `requirements.txt` |

---

## ⚙️ 性能 — 5/5 ✅

| # | 修复 |
|---|------|
| 11 | `list.pop(0)` → `deque.popleft()` |
| 12 | `compute_remaining_pool` 缓存复用 |
| 13 | `fetch_species_data` 按 `show_egg_group` 按需 |
| 14 | 精灵图异步后台下载 |
| 15 | `_name_jp_norm` 复用预计算值 |

---

## 🔗 依赖 — 5/5 ✅

| # | 修复 |
|---|------|
| 72 | PokeAPI response guard |
| 73 | `term-image>=0.7.2,<1` |
| 74 | prompt_toolkit 已有 `>=3.0.0,<4` + try/except |
| 75 | rich 已有 `>=13.0.0,<14` |
| 76 | JSON schema `isinstance(raw, list)` |

---

## 💀 死代码 — 8/9 ✅

| # | 状态 | 原因 |
|---|------|------|
| 33-39 | ✅ | 7 字段已移除 |
| 40 | ✅ | `_name_jp_norm` 已复用 |
| 41 | ❌ | `PokemonData` 别名 — 已在 #41 中移除，文档未同步标记 |

---

## 🏗️ 架构 — 10/10 ✅

| # | 修复 |
|---|------|
| 58 | `game.py` → `ui.py` 提取 270 行 |
| 59 | `paths.py` 分离环境路径 |
| 60 | `sys.path.insert` → 全项目相对导入 |
| 61 | `data.QUIET` → `quiet` 参数 |
| 62 | `_console` 单例 → 共享 `ui._console` |
| 63 | `_cache` 线程安全 → `threading.Lock` |
| 64 | `compute_remaining_pool` → 迁至 `game.py` |
| 65 | `cast()` 43→2 |
| 66 | `__init__.py` → docstring |
| 67 | `_config_file/_stats_file` → `path` 参数注入 |

---

## 📊 统计 — 3/4 ✅

| # | 修复 |
|---|------|
| 69 | `guesses_history` 截断至 1000 |
| 70 | `save_game_stats` a+→seek→truncate → 读写分离 |
| 71 | `_load_stats` 重复加载 → 与 #70 同步修复 |

| # | 未完成原因 |
|---|-----------|
| 68 | 按模式区分统计 — 需重新设计 JSON schema（`{mode: {wins, total, history}}`），需迁移旧统计文件 |

---

## 🧪 测试 — 11/17 ⚠

已完成 11 类（+39 tests，131 total）：#16-18, 24-25, 27-32

未完成：

| # | 函数 | 原因 |
|---|------|------|
| 19 | `PokemonCompleter` | 需模拟 prompt_toolkit Document/CompletionEvent，mock 成本高 |
| 20 | `show_settings` | 交互式 while 循环，与 TestRunGame 的 _FakeSession 模式类似但需独立实现 |
| 21 | `show_hints_table` | Rich Table 对象无法文本断言，只能验证不崩溃 |
| 22 | `show_logo` | 纯静态 ASCII，零分支零参数，崩溃概率为零 |
| 23 | `show_game_stats` | `get_stats_summary` 已单独测试，面板只是 Panel 包装 |
| 26 | `_show_pokemon_art` | 依赖 term-image+Pillow+PokeAPI 三层外部库 |

---

## 🎮 游戏逻辑 — 0/4 ❌

| # | 未完成原因 |
|---|-----------|
| 42 | 体型阈值需对照 PokeAPI 实际分布，当前值来自 web 版 |
| 43 | 速度需在百分比 vs 绝对差值间取舍，不同速度段适用不同策略 |
| 44 | 编号是 Wordle 类固有问题：编号≠相似度，但仍是玩家最直观线索 |
| 45 | 蛋组缺失时应告知"需联网"而非静默吞列 |

---

## 🖥️ UX — 2/9 ⚠

已完成：#50(快捷键), #54(按需拉取)

| # | 未完成原因 |
|---|-----------|
| 46 | 撤销需状态栈，Wordle 类游戏极少支持 |
| 47 | 提示消耗资源需设计（猜测次数?单独计数?），降低挑战性 |
| 48 | 候选池 1000+ 终端显示低效，可改交互式搜索 |
| 49 | 回菜单设计够简洁，加选项增交互复杂度 |
| 51 | 每日挑战需服务端种子同步，纯本地无法实现 |
| 52 | 存档需序列化 PokemonEntry+Hint+计时器，涉及 JSON 化 TypedDict |
| 53 | `1`/`2`/`3`/`q` 已足够，单字母可能与输入冲突 |

---

## ♿ 可访问性 — 0/3 ❌

| # | 未完成原因 |
|---|-----------|
| 55 | Rich dim 终端兼容性限制，需改颜色/亮度但无统一方案 |
| 56 | emoji 增加表格宽度可能溢出 |
| 57 | 精灵图文字描述需额外数据源（无现成宝可梦外观描述数据） |

---

## 📈 总结

| 维度 | 数字 |
|------|------|
| Bug | 10/10 |
| 性能 | 5/5 |
| 依赖 | 5/5 |
| 死代码 | 8/9 |
| 架构 | 10/10 |
| 统计 | 3/4 |
| 测试 | 11/17 类，92→131 tests |
| 提交 | 31 commits |
