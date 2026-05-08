# Code Review Report - pokemonle-tui
> Date: 2026-05-08
> Branch: master
> Total Files: 209
> Tech Stack: Python (13), JSON data (186), Rich TUI + prompt_toolkit + pytest

## 1. 项目概览

pokemonle-tui 是一个终端宝可梦猜谜游戏（类似 Wordle），使用 Python Rich 库渲染彩色表格界面。从 PokeAPI 获取额外数据，支持模糊匹配、前缀 Trie 搜索、统计追踪和分享结果。

- **核心**: Python 3 + Rich (TUI) + prompt_toolkit (交互补全)
- **数据**: 本地 JSON (14k 行宝可梦数据) + PokeAPI 缓存
- **测试**: pytest（类级别的模块测试）
- **架构**: 单文件入口 → `src/` 扁平模块（constants, data, comparison, fuzzy, game, stats, share, config）

209 文件中 186 个为 JSON（数据文件 + PokeAPI 缓存），核心 Python 源码仅 13 个文件。

## 2. 发现的问题

### 🔴 严重（Critical）

**无严重问题。** 纯本地终端应用，无网络暴露、无用户认证、无敏感数据处理。

### 🟡 警告（Warning）

1. **`_collect_ids` 使用 `list.pop(0)` — O(n) 出队** — `fuzzy.py:73`
   ```python
   cur = queue.pop(0)
   ```
   - `list.pop(0)` 的时间复杂度是 O(n)，对树遍历有性能影响
   - **建议**: 使用 `collections.deque` 替代 list 作为队列，`popleft()` 为 O(1)

2. **`find_pokemon` 的 `index` 参数类型为 `dict[object, PokemonEntry]`** — `fuzzy.py:163`
   - 使用 `object` 作为 key 类型失去了类型安全性
   - 虽然运行时正确（`int` 和 `str` 作为 key），但类型签名不够精确
   - **建议**: 使用 `dict[int | str, PokemonEntry]` 或 `TypedDict`

3. **`except ImportError: pass` 吞掉 prompt_toolkit 导入失败** — `game.py:30-32` 和 `fuzzy.py:192-239`
   - 如果 `prompt_toolkit` 版本不兼容导致部分 API 缺失，会在运行时崩溃而非导入时
   - `fuzzy.py` 中 `PokemonCompleter` 类使用了 `@override` 装饰器，如果导入对应类型失败会导致静默错误
   - **建议**: 在 `main()` 中添加 `prompt_toolkit` 可用性检查（已有，`game.py:255`）

### 🔵 建议（Suggestion）

1. **`sys.path.insert` hack** — `pokemonle.py` 使用 `sys.path.insert(0, 'src')` 来实现扁平导入
   - 这是为了解决 `from constants import ...` 在 `src/` 模块中的导入问题
   - **建议**: 改为相对导入或使用 `-m` 运行，消除 `sys.path` hack

2. **`try/except OSError: pass` 静默忽略统计保存失败** — `game.py:53-54`
   ```python
   except OSError:
       pass  # Already logged in save_game_stats
   ```
   - 虽然注释说已在 `save_game_stats` 中记录，但最好在此处也添加用户可见的提示

3. **`cast()` 过度使用** — 整个代码库大量使用 `cast()` 进行类型断言
   - 例如 `comparison.py` 中每个 `target["id"]` 都需要 `cast(int, ...)`
   - **建议**: 考虑使用 TypedDict 或 dataclass 来让类型系统自动推断

4. **`_trie` 未在 `get_fuzzy_matches` 中充分使用** — `fuzzy.py:139`
   - `get_fuzzy_matches` 接受可选的 `trie` 参数，但 `find_pokemon` 调用时未传入 trie
   - `find_pokemon` 的 index 是基于 dict 的 O(1) 查找，不需要 trie，逻辑正确但 trie 参数未被使用

## 3. 安全审查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 网络请求 | ✅ | 仅向 PokeAPI 发送 GET 请求（不传敏感数据） |
| 命令注入 | ✅ | 无 `os.system` / `subprocess` 调用 |
| 文件操作 | ✅ | 仅读写本地 JSON 文件 |
| 输入处理 | ✅ | 用户输入仅用于模糊匹配，无执行风险 |
| 依赖安全 | ✅ | 仅 3 个依赖（rich, prompt_toolkit, pytest） |

## 4. 性能分析

- **前缀 Trie 搜索**: 最近新增的 `PokemonTrie` 将自动补全从 O(n) 优化到 O(m)，性能良好
- **`list.pop(0)` 问题**: 见警告 #1，对大型 trie 子树有微小影响
- **PokeAPI 懒加载**: 之前已优化为延迟加载，避免启动阻塞
- **JSON 数据文件**: 14k 行一次性加载，启动内存约 2-5MB，可接受

## 5. 代码规范

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Python 类型注解 | ✅ | 大量使用类型注解 + `from __future__ import annotations` |
| 命名规范 | ✅ | snake_case 函数、PascalCase 类 |
| 模块结构 | ✅ | src/ 扁平化，按职责拆分 |
| 代码重复 | ✅ | `_compare_stat` 提取良好，消除重复 |
| 错误处理 | ⚠️ | `except OSError: pass` 可能隐藏问题 |
| 文档 | ✅ | AGENTS.md 详尽 + docstring 完整 |

## 6. 交互与功能

- **游戏体验**: Rich 彩色表格 + emoji 提示，终端游戏体验优秀
- **设置面板**: 交互式设置（游戏模式/世代/显示选项）
- **统计系统**: 胜负追踪 + 连胜 + 直方图
- **分享功能**: 生成分享结果文本
- **模糊补全**: 前缀 Trie + 中/英/日三语搜索
- **边界处理**: 空世代校验、重复猜测、歧义检测

## 7. 总结与下一步展望

- **健康度评分**: 8.5/10
- **Top 3 优先改进项**:
  1. `list.pop(0)` → `collections.deque` 优化出队性能
  2. 减少 `cast()` 使用，替换为 TypedDict/dataclass
  3. `sys.path.insert` hack 清理

- **下一步行动**: 项目质量高，维护良好。可考虑：增加更多游戏模式、i18n 多语言支持、打包为 pip 可安装包。
