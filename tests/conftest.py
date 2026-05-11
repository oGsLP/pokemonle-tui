import pytest

from src.constants import DEFAULT_CONFIG
from src.data import load_pokemon_data
from src.poketypes import ConfigDict, PokemonEntry


@pytest.fixture(scope="session")
def pokemon_list() -> list[PokemonEntry]:
    """加载完整宝可梦数据（整个测试会话共享）"""
    return load_pokemon_data()


@pytest.fixture
def pokemon_25(pokemon_list: list[PokemonEntry]) -> PokemonEntry:
    """皮卡丘"""
    return next(p for p in pokemon_list if p["id"] == 25)


@pytest.fixture
def pokemon_1(pokemon_list: list[PokemonEntry]) -> PokemonEntry:
    """妙蛙种子"""
    return next(p for p in pokemon_list if p["id"] == 1)


@pytest.fixture
def pokemon_4(pokemon_list: list[PokemonEntry]) -> PokemonEntry:
    """小火龙"""
    return next(p for p in pokemon_list if p["id"] == 4)


@pytest.fixture
def default_config() -> ConfigDict:
    return dict(DEFAULT_CONFIG)
