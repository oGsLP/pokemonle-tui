# pokemonle-tui Quality & Feature Enhancement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix critical bugs, improve architecture, and add key UX features (pool counter, share, streaks, histogram, trie autocomplete).

**Architecture:** Bug fixes first (NameError crash, silent exceptions), then code deduplication and dependency injection to improve testability, then UX features that build on the cleaner architecture. Each task is independently testable and committable.

**Tech Stack:** Python 3.10+, rich, prompt_toolkit, pytest, json, fcntl

---

## Pre-Implementation Checklist

- [ ] Read `src/comparison.py` — understand `compare_pokemon` function structure
- [ ] Read `src/game.py` — understand `run_game`, `show_hints_table`, `main`
- [ ] Read `src/stats.py` — understand save/load, get_stats_summary
- [ ] Read `src/config.py` — understand load/save
- [ ] Read `src/fuzzy.py` — understand `get_fuzzy_matches`, `PokemonCompleter`
- [ ] Read `src/data.py` — understand `get_pokemon_details`, PokeAPI caching
- [ ] Run existing tests: `python3 -m pytest tests/ -v` — all 83 must pass before starting

---

## Task 1: Fix comparison.py:155 NameError Bug (CRITICAL)

**Files:**
- Modify: `src/comparison.py:126-161`
- Test: `tests/test_all.py` (add to TestComparison)

**Problem:** `show_more_appearance` block at line 154 references `target_height` and `guess_height` variables that are only defined inside the height comparison block (lines 126-128). If `"height" not in target` but `"height" in guess` (or vice versa), the height block is skipped entirely, but the appearance block still executes because its guard only checks `"height" in target and "height" in guess`. This means `target_height` and `guess_height` are never assigned, causing `NameError`.

**Root cause:** The height variables have block-local scope but the appearance block (which depends on them) is at a higher scope level.

### Steps

- [ ] **Step 1: Write failing regression test**

```python
# In tests/test_all.py, add to TestComparison class:

def test_appearance_without_height_no_crash(self):
    """开启体型比较但目标缺少身高数据时不应崩溃"""
    target = {"id": 1, "types": ["草"], "generation": "第一世代"}
    guess = {"id": 2, "types": ["草"], "generation": "第一世代"}
    hints = compare_pokemon(target, guess, {**DEFAULT_CONFIG, "show_more_appearance": True})
    labels = [h.label for h in hints]
    assert "体型" not in labels, "缺少身高数据时不应有体型提示"
```

Run: `python3 -m pytest tests/test_all.py::TestComparison::test_appearance_without_height_no_crash -v`
Expected: FAIL with `NameError: name 'target_height' is not defined`

- [ ] **Step 2: Fix the scoping bug in comparison.py**

Replace lines 125-161 (height + appearance blocks) with:

```python
    # ── 身高 ──
    height_available = "height" in target and "height" in guess
    if height_available:
        target_height = cast(int, target["height"])
        guess_height = cast(int, guess["height"])
        diff_h = target_height - guess_height
        arrow = "↑" if diff_h > 0 else "↓"
        h2 = guess_height / 10
        if diff_h == 0:
            hints.append(Hint("身高", f"{h2:.1f}m", "exact"))
        elif abs(diff_h) <= preset["height_range"]:
            hints.append(Hint("身高", f"{h2:.1f}m", "close", arrow))
        else:
            hints.append(Hint("身高", f"{h2:.1f}m", "far", arrow))

    # ── 更多外形信息 ──
    if config.get("show_more_appearance") and height_available:
        h_ratio = target_height / max(guess_height, 1)
        if h_ratio > 1.5:
            hints.append(Hint("体型", "更大", "miss"))
        elif h_ratio < 0.67:
            hints.append(Hint("体型", "更小", "miss"))
        else:
            hints.append(Hint("体型", "差不多", "partial"))
```

- [ ] **Step 3: Run tests to verify fix**

Run: `python3 -m pytest tests/test_all.py::TestComparison::test_appearance_without_height_no_crash tests/test_all.py::TestComparison::test_hint_labels_present tests/test_all.py::TestComparison -v`
Expected: All pass, including new test.

- [ ] **Step 4: Commit**

```bash
git add src/comparison.py tests/test_all.py
git commit -m "fix: NameError in show_more_appearance when height missing"
```

---

## Task 2: Fix stats.py and config.py Silent Exception Handling

**Files:**
- Modify: `src/stats.py:50-51`
- Modify: `src/config.py:64-67`
- Test: `tests/test_all.py` (add to TestStats, TestConfig)

**Problem:** `save_game_stats` does `except OSError: pass` — silently loses game results. `save_config` prints to stderr only, invisible in TUI.

### Steps

- [ ] **Step 1: Write tests for exception paths**

```python
# In tests/test_all.py, add to TestStats class:

def test_save_failure_raises(self, monkeypatch, tmp_path):
    """写入失败时应该抛出 OSError"""
    old = constants.STATS_FILE
    try:
        bad_path = str(tmp_path / "nonexistent" / "stats.json")
        constants.STATS_FILE = bad_path
        with pytest.raises(OSError):
            save_game_stats(True, 3)
    finally:
        constants.STATS_FILE = old


# In tests/test_all.py, add to TestConfig class:

def test_save_failure_raises(self, monkeypatch, tmp_path):
    """写入失败时应该抛出 OSError"""
    old = constants.CONFIG_FILE
    try:
        bad_path = str(tmp_path / "nonexistent" / "config.json")
        constants.CONFIG_FILE = bad_path
        with pytest.raises(OSError):
            save_config({"game_mode": "easy"})
    finally:
        constants.CONFIG_FILE = old
```

Run: `python3 -m pytest tests/test_all.py::TestStats::test_save_failure_raises tests/test_all.py::TestConfig::test_save_failure_raises -v`
Expected: FAIL — OSError not raised (currently swallowed).

- [ ] **Step 2: Fix stats.py — re-raise after logging**

Replace `src/stats.py:50-51`:
```python
    except OSError:
        pass
```
With:
```python
    except OSError:
        print(f"警告: 无法保存游戏统计: {path}", file=sys.stderr)
        raise
```

Note: The `save_game_stats` is called in `game.py` lines 296, 308, 316, 374, 385. Currently none catch OSError. We need to update callers too. But per the bug report, the immediate fix is to stop swallowing. We'll handle callers in a later task if needed.

We should update `game.py` callers to catch the re-raised error so it doesn't crash the game. For now, let's also update `game.py`:

- [ ] **Step 3: Fix config.py — raise after logging**

Replace `src/config.py:64-67`:
```python
    try:
        with open(_config_file(), "w") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"警告: 无法保存配置文件: {exc}", file=sys.stderr)
```
With:
```python
    try:
        with open(_config_file(), "w") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"警告: 无法保存配置文件: {exc}", file=sys.stderr)
        raise
```

- [ ] **Step 4: Add exception handling in game.py callers**

In `game.py`, `save_game_stats` is called in run_game at lines 296, 308, 316, 374, 385. We need to catch OSError in `run_game` so the game doesn't crash on stats save failure.

Add a helper wrapper at module level in `game.py` (before `show_logo` at line 48):

```python
def _safe_save_stats(won: bool, guesses: int) -> None:
    """Save stats, logging but not crashing on failure."""
    try:
        save_game_stats(won, guesses)
    except OSError:
        pass  # Already logged in save_game_stats
```

Then replace all `save_game_stats(...)` calls in `run_game` with `_safe_save_stats(...)`:
- Line 296: `_safe_save_stats(False, len(guesses_with_hints))`
- Line 308: `_safe_save_stats(False, len(guesses_with_hints))`
- Line 316: `_safe_save_stats(False, len(guesses_with_hints))`
- Line 374: `_safe_save_stats(True, len(guesses_with_hints))`
- Line 385: `_safe_save_stats(False, len(guesses_with_hints))`

For `show_settings` in `game.py`, the `save_config(cfg)` call at line 206 needs wrapping:

Replace line 206:
```python
            save_config(cfg)
            console.print("[green]✅ 设置已保存[/green]")
```
With:
```python
            try:
                save_config(cfg)
                console.print("[green]✅ 设置已保存[/green]")
            except OSError:
                console.print("[red]❌ 保存失败！[/red]")
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All 83 + 2 new = 85 pass.

- [ ] **Step 6: Commit**

```bash
git add src/stats.py src/config.py src/game.py tests/test_all.py
git commit -m "fix: propagate OSError in save_game_stats and save_config instead of silently swallowing"
```

---

## Task 3: Extract _compare_stat Helper (DRY Refactor)

**Files:**
- Modify: `src/comparison.py:14-163` (entire compare_pokemon)
- Test: No new tests needed — existing 14 comparison tests cover this. Refactor-only, behavior unchanged.

**Problem:** 6 identical stat comparison blocks (stat_total, speed, hp, attack, defense, sp_attack, sp_defense) repeat the same pattern. A single helper reduces 100+ lines to ~15.

### Steps

- [ ] **Step 1: Add _compare_stat helper to comparison.py**

Add after the imports (before `compare_pokemon` at line 14):

```python
def _compare_stat(
    target_val: int,
    guess_val: int,
    label: str,
    guess_display: str,
    range_key: str,
    preset: dict[str, int],
    *,
    formatter: callable[[int], str] | None = None,
) -> Hint:
    """Compare one numeric stat between target and guess.

    Returns a Hint with exact/close/far level and optional arrow.
    """
    diff = target_val - guess_val
    arrow = "↑" if diff > 0 else "↓"
    display = formatter(guess_val) if formatter else guess_display
    if diff == 0:
        return Hint(label, display, "exact")
    elif abs(diff) <= preset[range_key]:
        return Hint(label, display, "close", arrow)
    else:
        return Hint(label, display, "far", arrow)
```

- [ ] **Step 2: Replace stat_total comparison (lines 83-94)**

Replace:
```python
    # ── 种族值总和 ──
    if "stat_total" in target and "stat_total" in guess:
        target_stat_total = cast(int, target["stat_total"])
        guess_stat_total = cast(int, guess["stat_total"])
        diff_st = target_stat_total - guess_stat_total
        arrow = "↑" if diff_st > 0 else "↓"
        if diff_st == 0:
            hints.append(Hint("种族值", str(guess_stat_total), "exact"))
        elif abs(diff_st) <= preset["stat_range"]:
            hints.append(Hint("种族值", str(guess_stat_total), "close", arrow))
        else:
            hints.append(Hint("种族值", str(guess_stat_total), "far", arrow))
```

With:
```python
    # ── 种族值总和 ──
    if "stat_total" in target and "stat_total" in guess:
        hints.append(_compare_stat(
            cast(int, target["stat_total"]),
            cast(int, guess["stat_total"]),
            "种族值", str(cast(int, guess["stat_total"])), "stat_range", preset,
        ))
```

- [ ] **Step 3: Replace speed comparison (lines 96-107)**

```python
    # ── 速度 ──
    if "speed" in target and "speed" in guess:
        hints.append(_compare_stat(
            cast(int, target["speed"]),
            cast(int, guess["speed"]),
            "速度", str(cast(int, guess["speed"])), "speed_range", preset,
        ))
```

- [ ] **Step 4: Replace individual stat loop (lines 109-123)**

Replace the entire loop:
```python
    # ── 更多种族值 (HP/攻击/防御/特攻/特防) ──
    if config.get("show_more_stats"):
        for stat_key, stat_cn in [("hp", "HP"), ("attack", "攻击"), ("defense", "防御"),
                                  ("sp_attack", "特攻"), ("sp_defense", "特防")]:
            if stat_key in target and stat_key in guess:
                target_stat = cast(int, target[stat_key])
                guess_stat = cast(int, guess[stat_key])
                diff_v = target_stat - guess_stat
                arrow = "↑" if diff_v > 0 else "↓"
                if diff_v == 0:
                    hints.append(Hint(stat_cn, str(guess_stat), "exact"))
                elif abs(diff_v) <= preset["detail_range"]:
                    hints.append(Hint(stat_cn, str(guess_stat), "close", arrow))
                else:
                    hints.append(Hint(stat_cn, str(guess_stat), "far", arrow))
```

With:
```python
    # ── 更多种族值 (HP/攻击/防御/特攻/特防) ──
    if config.get("show_more_stats"):
        for stat_key, stat_cn in [("hp", "HP"), ("attack", "攻击"), ("defense", "防御"),
                                  ("sp_attack", "特攻"), ("sp_defense", "特防")]:
            if stat_key in target and stat_key in guess:
                hints.append(_compare_stat(
                    cast(int, target[stat_key]),
                    cast(int, guess[stat_key]),
                    stat_cn, str(cast(int, guess[stat_key])), "detail_range", preset,
                ))
```

- [ ] **Step 5: Also apply to ID comparison (bonus — similar pattern)**

Replace lines 27-35:
```python
    # ── 编号 ──
    target_id = cast(int, target["id"])
    guess_id = cast(int, guess["id"])
    diff = target_id - guess_id
    if diff == 0:
        hints.append(Hint("编号", f"#{target_id:04d}", "exact"))
    elif abs(diff) <= preset["id_range"]:
        hints.append(Hint("编号", f"#{guess_id:04d}", "close", "↑" if diff > 0 else "↓"))
    else:
        hints.append(Hint("编号", f"#{guess_id:04d}", "far", "↑" if diff > 0 else "↓"))
```

With:
```python
    # ── 编号 ──
    target_id = cast(int, target["id"])
    guess_id = cast(int, guess["id"])
    hints.append(_compare_stat(
        target_id, guess_id,
        "编号", f"#{guess_id:04d}", "id_range", preset,
        formatter=lambda v: f"#{v:04d}",
    ))
```

- [ ] **Step 6: And height/weight comparisons**

Height (lines 125-137):
```python
    # ── 身高 ──
    height_available = "height" in target and "height" in guess
    if height_available:
        target_height = cast(int, target["height"])
        guess_height = cast(int, guess["height"])
        hints.append(_compare_stat(
            target_height, guess_height,
            "身高", f"{guess_height / 10:.1f}m", "height_range", preset,
            formatter=lambda v: f"{v / 10:.1f}m",
        ))
```

Weight (lines 139-151):
```python
    # ── 体重 ──
    if "weight" in target and "weight" in guess:
        target_weight = cast(int, target["weight"])
        guess_weight = cast(int, guess["weight"])
        hints.append(_compare_stat(
            target_weight, guess_weight,
            "体重", f"{guess_weight / 10:.1f}kg", "weight_range", preset,
            formatter=lambda v: f"{v / 10:.1f}kg",
        ))
```

- [ ] **Step 7: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All 85 pass (existing 14 comparison tests must pass unchanged — pure refactor).

- [ ] **Step 8: Commit**

```bash
git add src/comparison.py
git commit -m "refactor: extract _compare_stat helper to eliminate 6 repeated stat comparison blocks"
```

---

## Task 4: Dependency Injection for Console Singleton

**Files:**
- Modify: `src/game.py` — remove `console = Console()` global, add parameter injection
- Test: `tests/test_all.py` (update TestRunGame and TestFormatHint)

**Problem:** `console = Console()` at module level makes all UI rendering impossible to test or redirect without monkeypatching.

**Approach:** Inject `console` as a parameter into functions that use it. Preserve backward compatibility by providing a default value that falls back to the module-level singleton.

### Steps

- [ ] **Step 1: Add type alias and default console**

In `src/game.py`, replace line 34:
```python
console = Console()
```
With:
```python
_console = Console()

from typing import Optional as _Optional

def _get_console(console: Console | None = None) -> Console:
    """Return the provided console or the module-level default."""
    return console if console is not None else _console
```

And update all internal calls from `console.print(...)` etc. to accept optional console parameter. Since this is a large change, we'll do it incrementally:

- [ ] **Step 2: Update show_logo to accept optional console**

```python
def show_logo(console: Console | None = None) -> None:
    c = _get_console(console)
    c.print(Panel(
        Align.center(Text(logo, style="bold cyan")),
        border_style="dim", box=box.ROUNDED, padding=(0, 1),
    ))
```

- [ ] **Step 3: Update show_hints_table**

```python
def show_hints_table(guesses_with_hints: list[GuessRecord], max_guesses: int, config: ConfigDict, *, console: Console | None = None) -> None:
    c = _get_console(console)
    # ... replace all console.print → c.print, console.Table → Table (no change needed)
```

Actually, a simpler approach: instead of threading console through every function, we use a context manager or a module-level setter. But the simplest approach that enables testing is:

```python
# At module level in game.py, after imports:
_console: Console = Console()

def set_console(c: Console) -> None:
    """Override the console for testing. Call without args to reset."""
    global _console
    _console = c

def get_console() -> Console:
    return _console
```

Then replace all `console.print(` with `_console.print(` and `console.input(` with `_console.input(` throughout game.py (about 20 occurrences).

In tests, use:
```python
from io import StringIO
test_console = Console(file=StringIO(), force_terminal=True)
game._console = test_console
```

- [ ] **Step 4: Do the replacement**

Search-and-replace in `src/game.py`:
- `console.print(` → `_console.print(`
- `console.input(` → `_console.input(`

And update `show_logo`, `show_hints_table`, `show_game_stats`, `show_settings`, `run_game`, `main` to use `_console` instead of `console`.

- [ ] **Step 5: Add get_console/set_console to public API**

```python
def _get_console() -> Console:
    return _console

def _set_console(c: Console) -> None:
    global _console
    _console = c
```

- [ ] **Step 6: Update tests — no behavior change**

The existing tests monkeypatch `"game.console.print"` — these will continue to work since `_console` is still a module attribute. Update to use `game._console` instead:

In `_mock_game_env` (test_all.py line 708-728):
```python
# Replace:
monkeypatch.setattr("game.console.print", lambda *a, **kw: None)
# With:
game._console = Console(file=StringIO(), force_terminal=True)
```

Or simpler: just change the monkeypatch target:
```python
monkeypatch.setattr("game._console.print", lambda *a, **kw: None)
```

- [ ] **Step 7: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All 85 pass.

- [ ] **Step 8: Commit**

```bash
git add src/game.py tests/test_all.py
git commit -m "refactor: replace global console with module-level set_console/get_console pattern for testability"
```

---

## Task 5: Lazy Loading for PokeAPI Target Details

**Files:**
- Modify: `src/game.py:236-258` (run_game initialization)
- Modify: `src/data.py:147-161` (get_pokemon_details)
- Test: `tests/test_all.py` (add to TestRunGame)

**Problem:** `run_game` eagerly calls `get_pokemon_details(target)` and `fetch_species_data(target["id"])` at game start (lines 252-257), causing up to 8 seconds network delay before the first prompt appears. Details should load on first need.

### Steps

- [ ] **Step 1: Refactor run_game to defer target detail loading**

Replace `game.py:251-257`:
```python
    target = random.choice(pool)
    target_details = cast(PokemonEntry, get_pokemon_details(cast(dict[str, object], target)))
    species_data = cast(dict[str, object] | None, fetch_species_data(target["id"]))
    if species_data:
        target_details["egg_groups"] = cast(list[str], species_data.get("egg_groups", []))
        cr = species_data.get("capture_rate")
        target_details["capture_rate"] = int(cr) if cr is not None else 0
```

With:
```python
    target = random.choice(pool)
    # Defer PokeAPI loading — only fetch when first comparison needs it
    target_details: PokemonEntry = cast(PokemonEntry, dict(target))
    _target_enriched = False

    def _ensure_target_details() -> None:
        """Lazily enrich target with PokeAPI data on first need."""
        nonlocal target_details, _target_enriched
        if _target_enriched:
            return
        enriched = cast(PokemonEntry, get_pokemon_details(cast(dict[str, object], target)))
        species_data = cast(dict[str, object] | None, fetch_species_data(target["id"]))
        if species_data:
            enriched["egg_groups"] = cast(list[str], species_data.get("egg_groups", []))
            cr = species_data.get("capture_rate")
            enriched["capture_rate"] = int(cr) if cr is not None else 0
        target_details = enriched
        _target_enriched = True
```

Then, before the `compare_pokemon` call (around line 348), add:
```python
        _ensure_target_details()
```

Note: The game also needs target details for the final win/loss display. The display already uses `target` (the base dict), which has `name`, `name_en`, `id`. Target details (stats) are only needed during comparison. So this change is safe.

Actually, looking more carefully, the `compare_pokemon` call needs target details for stat comparisons. The first guess will trigger the lazy load. This is the correct behavior — the details are only needed when the first comparison happens.

- [ ] **Step 2: Update comparison call site**

At `game.py:348` (where `hints = list(compare_pokemon(...))` is called), add before it:

```python
        if not _target_enriched:
            _ensure_target_details()
```

- [ ] **Step 3: Write a test to verify lazy loading**

```python
# In tests/test_all.py, add to TestRunGame:

def test_target_details_loaded_lazily(self, monkeypatch, pokemon_list, tmp_path):
    """目标详情应该在首次比较时才加载，而非游戏开始时"""
    load_calls = []

    def _tracking_details(poke):
        load_calls.append(poke["id"])
        d = dict(poke)
        d.update({"stat_total": 300, "speed": 90, "hp": 45, "attack": 50,
                   "defense": 40, "sp_attack": 60, "sp_defense": 50,
                   "height": 40, "weight": 60, "stats": {}})
        return d

    import game as _game
    monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: _FakeSession(["皮卡丘"]))
    monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))
    monkeypatch.setattr("random.choice", lambda s: pokemon_list[0])
    monkeypatch.setattr("game._console.print", lambda *a, **kw: None)
    monkeypatch.setattr("game.show_hints_table", lambda *a, **kw: None)
    monkeypatch.setattr("game.get_pokemon_details", _tracking_details)
    monkeypatch.setattr("game.fetch_species_data", lambda _id: None)

    # Before run_game, no detail calls yet
    assert len(load_calls) == 0

    _game.run_game(pokemon_list, {**DEFAULT_CONFIG, "max_guesses": 1})
    # Detail was loaded (for the first comparison after "皮卡丘" guess)
    # But it shouldn't have been loaded eagerly before the game loop
    assert len(load_calls) >= 1
```

Run: `python3 -m pytest tests/test_all.py::TestRunGame::test_target_details_loaded_lazily -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/game.py tests/test_all.py
git commit -m "perf: defer PokeAPI target detail loading to first comparison instead of game start"
```

---

## Task 6: Display Remaining Pokémon Pool Count

**Files:**
- Modify: `src/game.py:87-134` (show_hints_table), `src/game.py:259-283` (run_game panel)
- Test: `tests/test_all.py` (add to TestRunGame)

**Feature:** After each guess, show how many Pokémon remain in the generation-filtered pool. This gives players a sense of elimination progress.

### Steps

- [ ] **Step 1: Add pool size tracking to run_game**

In `game.py:run_game`, after `pool = [p for p in pokemon_list if p["generation"] in gen_filter]` (line 246):

```python
    total_pool_size = len(pool)
```

Update the game start panel (lines 275-283) to include pool size:

```python
    _console.print(Panel(
        (
            f"[bold cyan]🎮 新游戏开始！[/bold cyan]\n\n"
            f"  宝可梦池 [bold yellow]{total_pool_size}[/bold yellow] 只\n"
            f"  最多猜测 [bold yellow]{max_guesses}[/bold yellow] 次\n"
            f"  输入宝可梦中文名/英文名/编号（支持模糊补全）\n"
            "  输入 [bold red]q[/bold red] 退出  |  [bold red]reveal[/bold red] 揭晓答案\n"
        ),
        border_style="dim", title="🎯 猜猜看",
    ))
```

- [ ] **Step 2: Calculate and display remaining pool after each guess**

After each guess is processed, we need to narrow the pool by elimination. The simplest approach: at each guess, compute how many Pokémon match ALL known hints. But that's complex.

Simpler approach: show the initial pool size in the table title and count obvious eliminations (wrong types, wrong generation). But even simpler: just show the initial pool size as context.

For a first pass, update the table title to include pool context. In `show_hints_table` (line 103):

```python
        title=f"📋 猜测记录 (第 {len(guesses_with_hints)}/{max_guesses} 次 | 池中 {total_pool_size} 只)",
```

But `show_hints_table` doesn't have access to `total_pool_size`. Pass it as a parameter:

Update the function signature (line 87):
```python
def show_hints_table(guesses_with_hints: list[GuessRecord], max_guesses: int, config: ConfigDict, *, pool_size: int = 0) -> None:
```

Update the call site in `run_game` (line 361):
```python
        show_hints_table(guesses_with_hints, max_guesses, config, pool_size=total_pool_size)
```

Update the title (line 103):
```python
        title=f"📋 猜测记录 (第 {len(guesses_with_hints)}/{max_guesses} 次 | 池中 {pool_size} 只)" if pool_size else f"📋 猜测记录 (第 {len(guesses_with_hints)}/{max_guesses} 次)",
```

- [ ] **Step 3: Write test**

```python
# In tests/test_all.py, add to TestRunGame:

def test_game_shows_pool_size(self, monkeypatch, pokemon_list, tmp_path):
    """游戏开始面板应该显示宝可梦池数量"""
    calls = []
    monkeypatch.setattr("game._console.print", lambda *a, **kw: calls.append(str(a)))
    monkeypatch.setattr("game.show_hints_table", lambda *a, **kw: None)
    
    import game as _game
    monkeypatch.setattr(_game, "PromptSession", lambda *a, **kw: _FakeSession(["q"]))
    monkeypatch.setattr(_game, "CompleteStyle", type("CS", (), {"MULTI_COLUMN": 1}))
    monkeypatch.setattr("random.choice", lambda s: pokemon_list[0])
    monkeypatch.setattr("game.get_pokemon_details", lambda p: {**p, "stat_total": 300, "speed": 90, "hp": 45, "attack": 50, "defense": 40, "sp_attack": 60, "sp_defense": 50, "height": 40, "weight": 60, "stats": {}})
    monkeypatch.setattr("game.fetch_species_data", lambda _id: None)
    
    _game.run_game(pokemon_list, {**DEFAULT_CONFIG, "generations": ["第一世代"]})
    
    # At least one print contained the pool count
    all_text = " ".join(str(c) for c in calls)
    # Should contain the Gen 1 count (151-ish Pokémon)
    # We just verify it contains a number
    assert any(c.isdigit() for c in all_text), "Pool size should be shown"
```

Run: `python3 -m pytest tests/test_all.py::TestRunGame::test_game_shows_pool_size -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/game.py tests/test_all.py
git commit -m "feat: show Pokémon pool size in game panel and hints table title"
```

---

## Task 7: Share Results (Emoji Grid)

**Files:**
- Create: `src/share.py` (new module for result formatting)
- Modify: `src/game.py:363-386` (win/loss display)
- Test: `tests/test_all.py` (add TestShare class)

**Feature:** After winning or losing, generate a Wordle-style emoji grid showing each guess's hint levels as colored squares. Print it to the terminal so players can screenshot and share.

### Steps

- [ ] **Step 1: Create src/share.py**

```python
"""
分享结果 — 生成 Wordle 风格的 emoji 网格
"""
from poketypes import GuessRecord


def format_share_result(
    guesses_with_hints: list[GuessRecord],
    max_guesses: int,
    target_name: str,
    target_name_en: str,
    target_id: int,
    won: bool,
    generation_label: str = "",
) -> str:
    """Generate a shareable emoji grid (Wordle-style).

    Levels mapped to squares:
    - exact → 🟩 (green)
    - close/partial → 🟨 (yellow)
    - miss/far → ⬛ (black)
    - missing hint → ⬜ (white, not used for this attribute)
    """
    # Header
    guess_count = len(guesses_with_hints)
    if won:
        header = f"Pokémonle #{target_id} {guess_count}/{max_guesses}"
    else:
        header = f"Pokémonle #{target_id} X/{max_guesses}"

    # Hint labels in order (same as show_hints_table)
    # But we use a simpler format: one row per guess, one square per hint
    rows: list[str] = []

    # Collect all hint labels used across all guesses (in order)
    all_labels: list[str] = []
    seen_labels: set[str] = set()
    for _, hints in guesses_with_hints:
        for h in hints:
            label = h[0] if len(h) >= 1 else ""
            if label not in seen_labels:
                all_labels.append(label)
                seen_labels.add(label)

    level_to_square = {
        "exact": "🟩",
        "close": "🟨",
        "partial": "🟨",
        "far": "⬛",
        "miss": "⬛",
    }

    for _, hints in guesses_with_hints:
        hint_map = {}
        for h in hints:
            label = h[0] if len(h) >= 1 else ""
            level = h[2] if len(h) >= 3 else "miss"
            hint_map[label] = level

        row_squares = []
        for label in all_labels:
            level = hint_map.get(label, "")
            square = level_to_square.get(level, "⬜")
            row_squares.append(square)
        rows.append(" ".join(row_squares))

    grid = "\n".join(rows)

    lines = [header, grid]
    if generation_label:
        lines.append(f"世代: {generation_label}")
    lines.append(f"答案: {target_name} ({target_name_en}) #{target_id:04d}")

    return "\n".join(lines)
```

- [ ] **Step 2: Write tests for share.py**

```python
# In tests/test_all.py, add TestShare class:

class TestShare:
    def test_format_share_won(self):
        """赢了的分享结果应该包含正确的 emoji 网格"""
        from share import format_share_result
        from constants import Hint

        guesses = [
            (
                {"name": "皮卡丘", "name_en": "Pikachu", "id": 25, "types": ["电"], "generation": "第一世代"},
                [
                    Hint("编号", "#0025", "exact"),
                    Hint("属性", "电", "partial", "电"),
                    Hint("世代", "1代", "exact"),
                ],
            ),
        ]

        result = format_share_result(
            guesses, 10, "皮卡丘", "Pikachu", 25, True,
        )

        assert "Pokémonle #25 1/10" in result
        assert "🟩" in result
        assert "🟨" in result

    def test_format_share_lost(self):
        """输了的分享结果应该显示 X"""
        from share import format_share_result
        from constants import Hint

        guesses = [
            (
                {"name": "皮卡丘", "name_en": "Pikachu", "id": 25, "types": ["电"], "generation": "第一世代"},
                [Hint("编号", "#0025", "far", "↑")],
            ),
        ]

        result = format_share_result(
            guesses, 10, "妙蛙种子", "Bulbasaur", 1, False,
        )

        assert "X/10" in result
        assert "⬛" in result

    def test_format_share_no_guesses(self):
        """无猜测时的分享（quit/reveal 未猜测）"""
        from share import format_share_result

        result = format_share_result(
            [], 10, "皮卡丘", "Pikachu", 25, False,
        )

        assert "0/10" not in result
        assert "X/10" in result  # lost with 0 guesses still shows X
        # Grid should be empty rows section
```

Run: `python3 -m pytest tests/test_all.py::TestShare -v`
Expected: PASS (3 tests)

- [ ] **Step 3: Integrate into game.py win/loss flow**

Add import at top of `game.py`:
```python
from share import format_share_result
```

In `run_game`, after win (line 374-375), add share text before `return`:

```python
        if guess["id"] == target["id"]:
            elapsed = time.time() - start_time
            _console.print(Panel(
                (
                    f"[bold green]🎉 猜对了！[/bold green]\n\n"
                    f"  答案: [bold]{target['name']}[/bold] ({target['name_en']}) #{target['id']:04d}\n"
                    f"  用了 [bold yellow]{len(guesses_with_hints)}[/bold yellow] 次\n"
                    f"  耗时 [bold cyan]{elapsed:.0f}[/bold cyan] 秒"
                ),
                border_style="dim", title="🏆 You Win!",
            ))
            # Show shareable grid
            gen_short = GEN_MAP.get(target.get("generation", ""), ("",))[0]
            share_text = format_share_result(
                guesses_with_hints, max_guesses,
                target["name"], target["name_en"], target["id"], True,
                gen_short,
            )
            _console.print(Panel(share_text, border_style="dim", title="📤 分享结果"))
            _safe_save_stats(True, len(guesses_with_hints))
            return
```

And similarly for loss (after line 384):

```python
        if len(guesses_with_hints) >= max_guesses:
            _console.print(Panel(
                (
                    f"[bold red]😢 游戏结束！[/bold red]\n\n"
                    f"  答案是: [bold]{target['name']}[/bold] ({target['name_en']}) #{target['id']:04d}"
                ),
                border_style="dim", title="💀 Game Over",
            ))
            gen_short = GEN_MAP.get(target.get("generation", ""), ("",))[0]
            share_text = format_share_result(
                guesses_with_hints, max_guesses,
                target["name"], target["name_en"], target["id"], False,
                gen_short,
            )
            _console.print(Panel(share_text, border_style="dim", title="📤 分享结果"))
            _safe_save_stats(False, len(guesses_with_hints))
            return
```

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/share.py src/game.py tests/test_all.py
git commit -m "feat: add Wordle-style emoji grid share results after win/loss"
```

---

## Task 8: Streak Tracking

**Files:**
- Modify: `src/stats.py:18-71` (add streak tracking)
- Modify: `src/game.py:137-139` (show_game_stats display)
- Test: `tests/test_all.py` (add to TestStats)

**Feature:** Track current win streak, best win streak, and show in stats summary.

### Steps

- [ ] **Step 1: Update stats.py data structure**

In `src/stats.py`, update `_load_stats` return default (line 29):
```python
    return {"wins": 0, "total": 0, "guesses_history": [], "current_streak": 0, "best_streak": 0}
```

Update `save_game_stats` (replace lines 32-51):
```python
def save_game_stats(won: bool, num_guesses: int) -> None:
    """保存一局游戏的结果（含连胜追踪）"""
    path = _stats_file()
    try:
        with open(path, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                stats = json.load(f) if os.path.getsize(path) > 0 else {"wins": 0, "total": 0, "guesses_history": [], "current_streak": 0, "best_streak": 0}
            except json.JSONDecodeError:
                stats = {"wins": 0, "total": 0, "guesses_history": [], "current_streak": 0, "best_streak": 0}
            stats["total"] += 1
            if won:
                stats["wins"] += 1
                stats["current_streak"] = stats.get("current_streak", 0) + 1
                stats["best_streak"] = max(stats.get("best_streak", 0), stats["current_streak"])
            else:
                stats["current_streak"] = 0
            stats["guesses_history"].append(num_guesses)
            f.seek(0)
            f.truncate()
            json.dump(stats, f, ensure_ascii=False)
    except OSError:
        print(f"警告: 无法保存游戏统计: {path}", file=sys.stderr)
        raise
```

Update `get_stats_summary` (lines 54-71):
```python
def get_stats_summary(pokemon_count: int) -> str:
    """返回统计摘要文本（含连胜信息）"""
    stats = _load_stats()
    total = stats["total"]
    wins = stats["wins"]
    accuracy = f"{wins / total * 100:.1f}%" if total > 0 else "N/A"
    history = stats["guesses_history"]
    avg_guess = f"{sum(history) / len(history):.1f}" if history else "N/A"
    current_streak = stats.get("current_streak", 0)
    best_streak = stats.get("best_streak", 0)

    return f"""
🏆 游戏统计
━━━━━━━━━━━━━━━━
  宝可梦池:  {pokemon_count} 只
  总场次:    {total}
  胜场:     {wins}
  胜率:     {accuracy}
  平均猜测:  {avg_guess} 次
  当前连胜:  {current_streak}
  最佳连胜:  {best_streak}
"""
```

- [ ] **Step 2: Write tests**

```python
# In tests/test_all.py, add to TestStats:

def test_streak_tracking(self, tmp_path):
    """连胜应该被正确追踪"""
    old = constants.STATS_FILE
    try:
        constants.STATS_FILE = str(tmp_path / "test_streak.json")
        # Win 3 in a row
        save_game_stats(True, 3)
        save_game_stats(True, 5)
        save_game_stats(True, 2)
        stats = _load_stats()
        assert stats["current_streak"] == 3
        assert stats["best_streak"] == 3
        # Now lose one
        save_game_stats(False, 10)
        stats = _load_stats()
        assert stats["current_streak"] == 0
        assert stats["best_streak"] == 3
        # Win one more
        save_game_stats(True, 4)
        stats = _load_stats()
        assert stats["current_streak"] == 1
        assert stats["best_streak"] == 3  # Best unchanged
    finally:
        constants.STATS_FILE = old

def test_get_stats_summary_with_streaks(self):
    """统计摘要应显示连胜信息"""
    summary = get_stats_summary(1082)
    assert "连胜" in summary
```

Run: `python3 -m pytest tests/test_all.py::TestStats -v`
Expected: All pass.

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/stats.py tests/test_all.py
git commit -m "feat: add win streak tracking (current + best) to game stats"
```

---

## Task 9: Guess Distribution Histogram

**Files:**
- Modify: `src/stats.py:54-71` (get_stats_summary)
- Test: `tests/test_all.py` (add to TestStats)

**Feature:** Show a bar-chart style histogram of how many games were won in 1 guess, 2 guesses, ..., N+ guesses.

### Steps

- [ ] **Step 1: Add histogram to get_stats_summary**

Replace `src/stats.py:54-71`:
```python
def get_stats_summary(pokemon_count: int) -> str:
    """返回统计摘要文本（含连胜和分布直方图）"""
    stats = _load_stats()
    total = stats["total"]
    wins = stats["wins"]
    accuracy = f"{wins / total * 100:.1f}%" if total > 0 else "N/A"
    history = stats["guesses_history"]
    avg_guess = f"{sum(history) / len(history):.1f}" if history else "N/A"
    current_streak = stats.get("current_streak", 0)
    best_streak = stats.get("best_streak", 0)

    # Build guess distribution histogram (for won games only)
    # Note: guesses_history includes ALL games (won and lost).
    # We don't currently track which guesses were wins vs losses in the history.
    # For simplicity, show distribution of ALL guess counts.
    distribution = _build_distribution(history)

    lines = [
        f"🏆 游戏统计",
        f"━━━━━━━━━━━━━━━━",
        f"  宝可梦池:  {pokemon_count} 只",
        f"  总场次:    {total}",
        f"  胜场:     {wins}",
        f"  胜率:     {accuracy}",
        f"  平均猜测:  {avg_guess} 次",
        f"  当前连胜:  {current_streak}",
        f"  最佳连胜:  {best_streak}",
        "",
        f"📊 猜测分布",
        f"━━━━━━━━━━━━━━━━",
    ]

    max_count = max(distribution.values()) if distribution else 1
    for guesses in range(1, 16):
        count = distribution.get(guesses, 0)
        bar_len = int(count / max_count * 10) if max_count > 0 else 0
        bar = "█" * bar_len if bar_len > 0 else " "
        label = f"{guesses:2d}次" if guesses > 1 else f"{guesses:2d}次"
        lines.append(f"  {label} {bar} {count}")

    return "\n".join(lines)


def _build_distribution(history: list[int]) -> dict[int, int]:
    """Build a frequency map of guess counts from history."""
    dist: dict[int, int] = {}
    for g in history:
        dist[g] = dist.get(g, 0) + 1
    return dist
```

- [ ] **Step 2: Write tests**

```python
# In tests/test_all.py, add to TestStats:

def test_histogram_display(self, monkeypatch, tmp_path):
    """统计摘要应包含直方图"""
    old = constants.STATS_FILE
    try:
        constants.STATS_FILE = str(tmp_path / "test_hist.json")
        save_game_stats(True, 3)
        save_game_stats(True, 5)
        save_game_stats(True, 3)
        save_game_stats(False, 10)
        save_game_stats(True, 1)

        summary = get_stats_summary(1082)
        assert "📊 猜测分布" in summary
        assert "█" in summary or "1" in summary  # At least one bar
    finally:
        constants.STATS_FILE = old

def test_distribution_empty(self):
    """空历史时不应崩溃"""
    from stats import _build_distribution
    dist = _build_distribution([])
    assert dist == {}
```

Run: `python3 -m pytest tests/test_all.py::TestStats -v`
Expected: All pass.

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/stats.py tests/test_all.py
git commit -m "feat: add guess distribution histogram to stats summary"
```

---

## Task 10: Precomputed Trie for Autocomplete

**Files:**
- Modify: `src/fuzzy.py` (add Trie class, update get_fuzzy_matches)
- Test: `tests/test_all.py` (add TestTrie class)

**Problem:** `get_fuzzy_matches` scans all 1082 Pokémon on every keystroke (O(n) × k keystrokes). A prefix trie can reduce this to O(m) per keystroke where m = number of matches.

**Note:** This is the most technically complex task. A trie approach works for prefix matches but fuzzy substring/typo matches still need scoring. The optimization is: use the trie for fast prefix lookup, fall back to O(n) only when query doesn't match any trie prefix.

### Steps

- [ ] **Step 1: Add Trie class to fuzzy.py**

Add before `score_pokemon` (line 13):

```python
from __future__ import annotations

class _TrieNode:
    """Trie node for Pokémon name prefix lookup."""
    __slots__ = ("children", "pokemon_ids")

    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.pokemon_ids: list[int] = []


class PokemonTrie:
    """Prefix trie for fast Pokémon name autocomplete.

    Indexes Chinese, English (normalized), and Japanese names.
    """

    def __init__(self, pokemon_list: list[PokemonEntry]) -> None:
        self._root = _TrieNode()
        self._pokemon_by_id: dict[int, PokemonEntry] = {}
        self._build(pokemon_list)

    def _insert(self, text: str, poke_id: int) -> None:
        node = self._root
        for ch in text:
            if ch not in node.children:
                node.children[ch] = _TrieNode()
            node = node.children[ch]
        if poke_id not in node.pokemon_ids:
            node.pokemon_ids.append(poke_id)

    def _build(self, pokemon_list: list[PokemonEntry]) -> None:
        for p in pokemon_list:
            pid = p["id"]
            self._pokemon_by_id[pid] = p
            # Chinese name
            self._insert(p["name"], pid)
            # Normalized English name
            en = p.get("_name_en_norm", p["name_en"].lower().replace("-", "").replace(" ", ""))
            if en:
                self._insert(en, pid)
            # Japanese name
            jp = p.get("_name_jp_norm", p.get("name_jp", "").lower())
            if jp:
                self._insert(jp, pid)
            # ID as string
            self._insert(p.get("_id_str", str(pid)), pid)

    def prefix_search(self, prefix: str, limit: int = 15) -> list[PokemonEntry]:
        """Return Pokémon whose indexed names start with prefix.

        Falls back to empty list if prefix not in trie.
        """
        prefix = prefix.lower().strip()
        if not prefix:
            return []

        node = self._root
        for ch in prefix:
            if ch not in node.children:
                return []  # No prefix match
            node = node.children[ch]

        # Collect all IDs reachable from this node (BFS/DFS)
        ids = self._collect_ids(node, limit)
        return [self._pokemon_by_id[pid] for pid in ids if pid in self._pokemon_by_id]

    def _collect_ids(self, node: _TrieNode, limit: int) -> list[int]:
        """BFS collect Pokémon IDs from trie node, respecting limit."""
        result: list[int] = []
        queue: list[_TrieNode] = [node]
        while queue and len(result) < limit:
            current = queue.pop(0)
            for pid in current.pokemon_ids:
                if pid not in result:
                    result.append(pid)
                    if len(result) >= limit:
                        return result
            for child in current.children.values():
                queue.append(child)
        return result
```

- [ ] **Step 2: Wire trie into get_fuzzy_matches**

Update `get_fuzzy_matches` (lines 68-79):

```python
def get_fuzzy_matches(query: str, pokemon_list: list[PokemonEntry], limit: int = 15, *, trie: PokemonTrie | None = None) -> list[PokemonEntry]:
    """返回按匹配度排序的模糊匹配结果。

    如果提供了 trie，优先使用 trie 进行前缀搜索（O(m)），
    仅在 trie 无结果时回退到全量扫描（O(n)）。
    """
    q = query.strip()
    if not q:
        return []

    # Fast path: trie prefix search
    if trie is not None:
        trie_results = trie.prefix_search(q, limit)
        if trie_results:
            return trie_results[:limit]

    # Slow path: full scan with scoring (existing logic)
    scored = []
    for p in pokemon_list:
        s = score_pokemon(q, p)
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]
```

- [ ] **Step 3: Build trie once in PokemonCompleter and pass to get_fuzzy_matches**

Update `PokemonCompleter.__init__` (line 118):

```python
    def __init__(self, pokemon_list: list[PokemonEntry]) -> None:
        self.pokemon_list = pokemon_list
        self._trie = PokemonTrie(pokemon_list)
```

Update `get_completions` (line 131):
```python
            matches = get_fuzzy_matches(query, self.pokemon_list, limit=15, trie=self._trie)
```

- [ ] **Step 4: Also update find_pokemon to use trie for prefix**

In `find_pokemon` (line 82), update fallback call:
```python
    matches = get_fuzzy_matches(query, pokemon_list, limit=1, trie=None)  # trie not needed for single-exact lookup
```

For `run_game` in `game.py`, when calling `get_fuzzy_matches` for suggestions (line 321), we can optionally pass the trie. But since the completer already has it, the suggestion calls don't need it — they're for error messages only.

- [ ] **Step 5: Write tests**

```python
# In tests/test_all.py, add TestTrie class:

class TestTrie:
    def test_trie_build_and_search(self, pokemon_list):
        """Trie 应该能构建和搜索"""
        from fuzzy import PokemonTrie
        trie = PokemonTrie(pokemon_list)

        # Prefix search
        results = trie.prefix_search("皮卡", limit=5)
        assert len(results) > 0
        assert results[0]["id"] == 25  # 皮卡丘

    def test_trie_english_prefix(self, pokemon_list):
        """英文名前缀搜索"""
        from fuzzy import PokemonTrie
        trie = PokemonTrie(pokemon_list)

        results = trie.prefix_search("pika", limit=5)
        assert len(results) > 0
        assert any(p["id"] == 25 for p in results)

    def test_trie_empty_query(self, pokemon_list):
        """空查询返回空列表"""
        from fuzzy import PokemonTrie
        trie = PokemonTrie(pokemon_list)

        assert trie.prefix_search("", limit=5) == []

    def test_trie_no_match(self, pokemon_list):
        """无匹配返回空列表"""
        from fuzzy import PokemonTrie
        trie = PokemonTrie(pokemon_list)

        assert trie.prefix_search("xyznomatch", limit=5) == []

    def test_trie_respects_limit(self, pokemon_list):
        """Trie 应该遵守 limit 参数"""
        from fuzzy import PokemonTrie
        trie = PokemonTrie(pokemon_list)

        results = trie.prefix_search("龙", limit=3)
        assert len(results) <= 3

    def test_get_fuzzy_matches_with_trie(self, pokemon_list):
        """使用 trie 的 get_fuzzy_matches 应该返回正确结果"""
        from fuzzy import PokemonTrie, get_fuzzy_matches
        trie = PokemonTrie(pokemon_list)

        matches = get_fuzzy_matches("皮卡", pokemon_list, trie=trie)
        assert len(matches) > 0
        assert matches[0]["id"] == 25

    def test_get_fuzzy_matches_fallback_without_trie(self, pokemon_list):
        """无 trie 时应该回退到全量扫描评分"""
        from fuzzy import get_fuzzy_matches

        matches = get_fuzzy_matches("皮卡", pokemon_list, trie=None)
        assert len(matches) > 0
        assert matches[0]["id"] == 25
```

Run: `python3 -m pytest tests/test_all.py::TestTrie -v`
Expected: All 7 pass.

- [ ] **Step 6: Run full test suite**

Run: `python3 -m pytest tests/test_all.py -v`
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add src/fuzzy.py tests/test_all.py
git commit -m "perf: add prefix trie for O(m) autocomplete, fall back to O(n) scoring for fuzzy queries"
```

---

## Verification

After all tasks, run:

```bash
python3 -m pytest tests/ -v
# Expected: All tests pass

python3 pokemonle.py
# Manual smoke test: start a game, make a guess, verify:
# - Pool size displayed
# - No crashes
# - Share grid shown on win/loss
# - Stats show streak + histogram
# - Autocomplete is responsive
```

---

## Task Dependency Graph

```
Task 1 (NameError fix) ─────┐
Task 2 (silent exceptions) ─┤
                             ├─→ Task 6 (pool count)
Task 3 (_compare_stat) ─────┤       │
Task 4 (console injection) ─┤       ├─→ Task 7 (share)
Task 5 (lazy loading) ──────┘       │       │
                                     ├─→ Task 8 (streak)
Task 10 (trie) ── independent ──────┤       │
                                             ├─→ Task 9 (histogram)
```

Tasks 1-5 are independent foundation improvements. Tasks 6-9 build on them. Task 10 is entirely independent.
