"""Rebuild bot/data/bomb_prompts.json from bot/data/dictionary.txt.

Counts how many dictionary words contain each 2 and 3 letter fragment and keeps
the ones with enough matches to be a fair prompt. Run it only when the dictionary
changes; the bot just loads the result.

    python scripts/build_bomb_prompts.py
"""

import json
from collections import Counter
from pathlib import Path

MIN_MATCHES = 40  # a fragment needs at least this many words to be playable

DATA = Path(__file__).resolve().parent.parent / "bot" / "data"


def main():
    words = DATA.joinpath("dictionary.txt").read_text(encoding="utf-8").split()
    counts = Counter()
    for word in words:
        fragments = set()
        for size in (2, 3):
            for i in range(len(word) - size + 1):
                fragments.add(word[i : i + size])
        counts.update(fragments)

    prompts = {f: n for f, n in sorted(counts.items()) if n >= MIN_MATCHES}
    DATA.joinpath("bomb_prompts.json").write_text(json.dumps(prompts, indent=0), encoding="utf-8")
    print(f"{len(words):,} words -> {len(prompts):,} prompts (>= {MIN_MATCHES} matches)")


if __name__ == "__main__":
    main()
