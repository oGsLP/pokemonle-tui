# Code Review Report - pokemonle-tui
> Date: 2026-05-09
> Branch: master
> Total Files: 273
> Tech Stack: Python 3, Rich (TUI), prompt_toolkit, PokeAPI (REST), Pillow, term-image

## 1. 项目概览

Pokemonle TUI 是一款终端宝可梦竞猜游戏（类似 Wordle）。玩家通过输入宝可梦名称猜目标宝可梦，根据属性、身高、体重、类型等获得提示反馈。使用 Python 3 编写，基于 Rich 构建 TUI 界面，prompt_toolkit 提供交互式模糊补全，PokeAPI 获取详细宝可梦数据。项目规模适中（273 文件，其中 243 为 JSON 缓存数据），结构清晰。

## 2. 发现的问题

### 🔴 严重（Critical）

1. **重复 API 调用 Bug** — `src/data.py:167-168`
   ```python
   api_data = fetch_pokeapi_data(poke["id"], quiet=quiet)
   api_data = fetch_pokeapi_data(poke["id"], quiet=quiet)  # 重复调用！
   ```
   - `get_pokemon_details()` 函数中第 167 和 168 行重复调用了 `fetch_pokeapi_data`，第二个调用覆盖了第一个结果
   - 影响：每次获取宝可梦详情时浪费一次 PokeAPI 请求，增加延迟、浪费带宽、可能触发 API 限流
   - 修复：删除第 167 行即可

### 🟡 警告（Warning）

1. **目标宝可梦详情线程生命周期管理不完善** — `src/game.py:101-118`
   - `_fetch_target` 线程设置为 `daemon=True`，但游戏退出时线程可能仍在运行
   - `_target_done.wait(timeout=8)` 超时后线程继续运行但游戏已继续
   - 风险：线程在后台持续运行但无人等待其结果
   - 建议：线程结束后将结果写入共享状态，并在游戏结束时主动 join

2. **PokeAPI 请求无重试机制** — `src/data.py:92-108`
   - `_cached_or_fetch` 中网络请求失败直接返回 None，无重试
   - PokeAPI 作为免费服务可能偶尔超时或 429
   - 建议：添加指数退避重试（至少 2-3 次）

3. **Sprite 缓存无限增长** — `.sprite_cache/` 目录
   - 精灵图片缓存未设置大小限制或过期清理策略
   - 建议：添加 LRU 淘汰或最大缓存文件数限制

### 🔵 建议（Suggestion）

1. **`_safe_save_stats` 吞掉所有 OSError** — `src/game.py:35-39`
   - 统计保存失败时静默忽略，用户无法得知数据丢失
   - 建议：至少记录警告日志或显示一次性提示

2. **恶作剧模式 (`mischief`) 的随机性依赖 `random.choice`** — `src/game.py:230`
   - 箭头方向随机反转，非确定性行为，娱乐性功能，影响不大
   - 建议：在设置界面明确说明恶作剧模式的效果

3. **`PokemonEntry` 类型松散** — 使用 `TypedDict` 定义，但多处使用 `.get()` 和 `update()`
   - `get_pokemon_details` 返回值使用 `type: ignore[typeddict-unknown-key]`
   - 建议：考虑使用 dataclass 或 Pydantic 模型增强类型安全

4. **缺少输入长度限制** — `session.prompt()` 无 `max_length`
   - 建议：添加合理的输入长度限制

## 3. 安全审查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 硬编码密钥 | ✅ | 无，PokeAPI 为公开 API 无需密钥 |
| 注入风险 | ✅ | 无 eval/exec/shell=True，纯 Python 处理 |
| 依赖安全 | ✅ | rich, prompt_toolkit, Pillow, term-image 均为知名库 |
| 数据安全 | ✅ | 本地 JSON 文件存储，无网络传输敏感数据 |
| SSL/TLS | ✅ | PokeAPI 请求使用 `ssl.create_default_context()` |
| 用户输入 | ✅ | 所有用户输入通过 prompt_toolkit 和 `find_pokemon` 校验 |

## 4. 性能分析

- ✅ 本地 JSON 数据文件 + PokeAPI 缓存减少网络请求
- ✅ 原子文件写入 (`os.replace`) 防止缓存损坏
- ✅ `build_pokemon_index` 提供 O(1) 查找
- ❌ 重复 API 调用 Bug（见 Critical 问题）
- ⚠️ `compute_remaining_pool` O(N×M) 复杂度（N=candidates, M=guesses），在大池模式下可能较慢

## 5. 代码规范

- ✅ 类型注解使用（TypedDict, NamedTuple, Callable, 泛型）
- ✅ 函数文档字符串（docstring）完善
- ✅ 清晰的模块划分：`data.py`、`game.py`、`comparison.py`、`ui.py`、`stats.py`
- ✅ 测试文件存在（`tests/test_all.py`，12+ 测试）
- ✅ 中文注释与代码混合，风格一致
- ⚠️ `sys.path.insert` 导入方式（`pokemonle.py:5-6`），非标准但文档已说明原因

## 6. 交互与功能

- ✅ Rich 面板美观，支持彩色输出和 spinner
- ✅ prompt_toolkit 模糊补全体验良好
- ✅ 多世代可选、显示/隐藏蛋群等设置
- ✅ 游戏统计、分享结果格式化
- ✅ 恶作剧模式增加趣味性
- ⚠️ 答案揭晓使用 `threading.Event` 超时 8 秒可能让用户等待

## 7. 总结与下一步展望

- **项目整体健康度评分：7/10**
- **Top 3 优先改进项：**
  1. 修复 `get_pokemon_details` 中的重复 API 调用（Critical Bug）
  2. 添加网络请求重试机制
  3. 改进后台线程生命周期管理
- **下一步行动建议：**
  - 添加 sprite 缓存 LRU 清理
  - 统计数据保存失败时添加警告日志
  - 考虑使用 `asyncio` 替代 `threading` 提升 I/O 并发
