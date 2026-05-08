"""
Shared type definitions for Pokemonle TUI.

This module provides the canonical type definitions used across all other modules.
All modules should import PokemonEntry and related types from here, NOT define
their own copies.
"""
from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from constants import Hint


class PokemonEntry(TypedDict, total=False):
    """Canonical Pokemon data entry.

    Fields from pokemon_full_list.json are always present (Required).
    Fields from PokeAPI enrichment are optional (NotRequired).
    """

    # ── Required: from pokemon_full_list.json ──
    id: Required[int]
    name: Required[str]
    name_en: Required[str]
    name_jp: Required[str]
    types: Required[list[str]]
    generation: Required[str]
    # Legacy field (same as id)
    index: Required[str]

    # ── Optional: from PokeAPI pokemon endpoint ──
    height: NotRequired[int]
    weight: NotRequired[int]
    stats: NotRequired[dict[str, int]]
    abilities: NotRequired[list[str]]
    stat_total: NotRequired[int]
    speed: NotRequired[int]
    hp: NotRequired[int]
    attack: NotRequired[int]
    defense: NotRequired[int]
    sp_attack: NotRequired[int]
    sp_defense: NotRequired[int]

    # ── Optional: from PokeAPI species endpoint ──
    egg_groups: NotRequired[list[str]]
    capture_rate: NotRequired[int]
    hatch_counter: NotRequired[int]
    gender_rate: NotRequired[int]
    is_legendary: NotRequired[bool]
    is_mythical: NotRequired[bool]
    growth_rate: NotRequired[str]
    shape: NotRequired[str]
    habitat: NotRequired[str]


# ── Legacy type aliases (for backward compatibility during migration) ──

# Used by comparison.py: target/guess dictionaries
PokemonData = PokemonEntry

# Config dictionary (settings keys → values)
ConfigDict = dict[str, object]

# A single hint record (Hint NamedTuple or plain tuple)
HintRecord = Hint | tuple[str, str, str] | tuple[str, str, str, str | None]

# A guess entry: (pokemon, list of hints)
GuessRecord = tuple[PokemonEntry, list[HintRecord]]
