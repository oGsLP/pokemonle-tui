import os

PROJECT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE: str = os.path.join(PROJECT_DIR, "pokemon_full_list.json")
CACHE_DIR: str = os.path.join(PROJECT_DIR, ".pokeapi_cache")
STATS_FILE: str = os.path.join(PROJECT_DIR, ".game_stats.json")
CONFIG_FILE: str = os.path.join(PROJECT_DIR, ".game_config.json")
