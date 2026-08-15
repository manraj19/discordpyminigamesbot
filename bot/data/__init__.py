"""Static game data, loaded once from the JSON files in this package."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent


def _load(name):
    with open(_DATA_DIR / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)


def _load_lines(name):
    with open(_DATA_DIR / f"{name}.txt", encoding="utf-8") as fh:
        return set(fh.read().split())


COUNTRIES = _load("countries")  # {alpha2_code: country_name}
TRUTH = _load("truth")  # list[str]
DARE = _load("dare")  # list[str]
RIDDLES = _load("riddles")  # list[{"question", "answer"}]
EIGHT_BALL = _load("eight_ball")  # list[str]
WORDS = _load("words")  # list[str] of 5-letter words
EMOJI_PUZZLES = _load("emoji_puzzles")  # list[{"clue", "answer"}]

# Bomb Party: the full ENABLE word list (public domain) and the prompt fragments
# built from it by scripts/build_bomb_prompts.py. ~9 MB of strings, loaded once
# per process, so it does not scale with the number of servers.
DICTIONARY = _load_lines("dictionary")  # set[str]
BOMB_PROMPTS = _load("bomb_prompts")  # {fragment: how many words contain it}

_cricket = _load("cricket_names")  # {"batsmen": [...], "bowlers": [...]}
CRICKET_BATSMEN = _cricket["batsmen"]
CRICKET_BOWLERS = _cricket["bowlers"]
CRICKET_NAMES = CRICKET_BATSMEN + CRICKET_BOWLERS
