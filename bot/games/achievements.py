"""Achievement catalogue and evaluation. Pure: no discord, no DB.

Each achievement is (name, description, condition) where condition takes a stats
dict and returns True once earned. The bot gathers the stats from its services
and grants any newly met achievements.
"""

# id -> (name, description, condition(stats) -> bool)
ACHIEVEMENTS = {
    "first_win": ("First Blood", "Win your first game.", lambda s: s["total_score"] >= 1),
    "rich": ("Rich", "Hold 1,000 MiniCoins at once.", lambda s: s["coins"] >= 1000),
    "loaded": ("Loaded", "Hold 10,000 MiniCoins at once.", lambda s: s["coins"] >= 10000),
    "dedicated": ("Dedicated", "Reach a 7-day daily streak.", lambda s: s["streak"] >= 7),
    "duelist": ("Duelist", "Win your first duel.", lambda s: s["duel_wins"] >= 1),
    "gladiator": ("Gladiator", "Win 10 duels.", lambda s: s["duel_wins"] >= 10),
    "contender": ("Contender", "Reach 1,200 duel rating.", lambda s: s["duel_rating"] >= 1200),
}


def evaluate(stats):
    """Return the ids of every achievement whose condition is met for these stats."""
    return [aid for aid, (_name, _desc, condition) in ACHIEVEMENTS.items() if condition(stats)]
