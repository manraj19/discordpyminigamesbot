"""Flagle rules: is this message the right country, the wrong one, or no country?

A run shouldn't end over spelling. Names compare without case, accents or
punctuation, common alternatives count (bot/data/country_aliases.json), and a
close typo of the right answer passes. Only naming another country outright is
wrong, so "no way" or "macau" just cost a little time.
"""

import difflib
import re
import unicodedata

from bot.data import COUNTRIES, COUNTRY_ALIASES

TYPO_CUTOFF = 0.8
MAX_GUESS_LENGTH = 40  # longer than any name, and keeps difflib cheap on a pasted essay


def normalize(text):
    """'St. Kitts & Nevis' and 'saint kitts and nevis' come out the same."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"(?<=\b\w)\.", "", text)  # u.s.a -> usa
    text = re.sub(r"['’`]", "", text).replace("&", " and ")  # d'ivoire -> divoire
    words = re.sub(r"[^a-z0-9]+", " ", text).split()
    if words and words[0] == "the":
        words = words[1:]
    return " ".join("saint" if word == "st" else word for word in words)


# Every way to name a country, mapped to who it names. A name can belong to two
# countries: "congo" and "korea" are right for either flag.
_NAMES = {}
for _code, _name in COUNTRIES.items():
    for _label in (_name, *COUNTRY_ALIASES.get(_code, ())):
        _NAMES.setdefault(normalize(_label), set()).add(_code)


def judge(guess, code, previous=None):
    """Judge one message against the flag ``code``. Returns 'right', 'wrong' (it
    names another country), 'repeat' (the last flag's answer again, which got sent
    twice while the screen caught up) or 'unknown' (not a country, so it's ignored).

    ponytail: a deliberate misspelling is a free guess, since a typo of a wrong
    country is only 'unknown'. Add a per-flag strike limit if the leaderboard gets gamed."""
    text = normalize(guess)
    if len(text) > MAX_GUESS_LENGTH:
        return "unknown"
    exact = _NAMES.get(text)
    close = difflib.get_close_matches(text, _NAMES, n=1, cutoff=TYPO_CUTOFF) if not exact else None
    named = exact or (_NAMES[close[0]] if close else ())
    if code in named:
        return "right"
    if previous in named:
        return "repeat"
    return "wrong" if exact else "unknown"
