"""Static game data, loaded once from the JSON files in this package."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent


def _load(name):
    with open(_DATA_DIR / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)


COUNTRIES = _load("countries")  # {alpha2_code: country_name}
CRICKET_NAMES = _load("cricket_names")  # list[str]
TRUTH = _load("truth")  # list[str]
DARE = _load("dare")  # list[str]
RIDDLES = _load("riddles")  # list[{"question", "answer"}]
EIGHT_BALL = _load("eight_ball")  # list[str]
