# AGENTS.md — Pokemonle TUI

Pokemon Wordle game in a terminal, based on QuantAskk/pokemonle data.

## Commands

```bash
# run
python3 pokemonle.py

# test all
python3 -m pytest tests/ -v

# test one class
python3 -m pytest tests/test_all.py::TestComparison -v

# install deps (no venv by default)
pip install rich prompt_toolkit
```

## Architecture

```
pokemonle.py          # entry — patches sys.path, calls game.main()
src/
  constants.py        # paths, TYPE_COLORS, GEN_MAP, GAME_MODE_PRESETS, Hint(NamedTuple)
  data.py             # load_pokemon_data(), build_pokemon_index(), fetch_pokeapi_data(), fetch_species_data()
  config.py           # load/save .game_config.json
  comparison.py       # compare_pokemon(target, guess, config) → list[Hint]
  fuzzy.py            # find_pokemon(), get_fuzzy_matches(), PokemonCompleter
  game.py             # main(), run_game(), show_hints_table(), show_settings(), _format_hint()
  stats.py            # save_game_stats(), get_stats_summary()
tests/test_all.py     # pytest — class per module, session-scoped pokemon_list fixture
```

## Gotchas

- **`sys.path.insert`** in `pokemonle.py` is required — `src/` modules use flat imports (`from constants import ...`)
- **`git push` hangs** via `rtk` wrapper — use `GIT_TERMINAL_PROMPT=0 timeout 20 git push origin master`
- **`rtk` prefix** on most commands is the local shell wrapper

## Type matching display

`_format_hint` handles `属性` specially:
- matching types: full type color (e.g. `#78C850` for grass)
- non-matching types: `dim` type color — **do not use bold, it's invisible on some terminals**
- comparison sends matched types via `extra` field; `_format_hint` parses it as a set

## Hint type

`Hint(NamedTuple)` with fields `(label, value, level, arrow=None)`. Callers access by index (`h[0]`) or name (`h.label`).

## Data files

- `pokemon_full_list.json` — 14k lines, essential, committed
- `.game_config.json` / `.game_stats.json` — user-local, gitignored
- `.pokeapi_cache/` — runtime cache, gitignored
