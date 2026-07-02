"""Achievement catalogue and evaluation. Pure: no discord, no DB.

Each achievement is (name, description, reward, condition) where reward is the
MiniCoins granted on unlock and condition takes a stats dict and returns True
once earned. The bot gathers the stats from its services, grants any newly met
achievements, pays the reward, and announces it through the reward pipeline.

More achievements that need stats introduced by later phases (arena floors,
seasons, distinct-game wins) are added in those phases.
"""

# id -> (name, description, reward, condition(stats) -> bool)
ACHIEVEMENTS = {
    "first_win": ("First Blood", "Win your first game.", 50, lambda s: s["total_score"] >= 1),
    "veteran": ("Veteran", "Reach 1,000 total score.", 150, lambda s: s["total_score"] >= 1000),
    "prodigy": ("Prodigy", "Reach 10,000 total score.", 500, lambda s: s["total_score"] >= 10000),
    "rich": ("Rich", "Hold 1,000 MiniCoins at once.", 250, lambda s: s["coins"] >= 1000),
    "loaded": ("Loaded", "Hold 10,000 MiniCoins at once.", 1000, lambda s: s["coins"] >= 10000),
    "tycoon": ("Tycoon", "Hold 50,000 MiniCoins at once.", 2500, lambda s: s["coins"] >= 50000),
    "dedicated": ("Dedicated", "Reach a 7-day daily streak.", 250, lambda s: s["streak"] >= 7),
    "devoted": ("Devoted", "Reach a 30-day daily streak.", 1000, lambda s: s["streak"] >= 30),
    "centurion": ("Centurion", "Reach a 100-day daily streak.", 2500, lambda s: s["streak"] >= 100),
    "duelist": ("Duelist", "Win your first duel.", 100, lambda s: s["duel_wins"] >= 1),
    "gladiator": ("Gladiator", "Win 10 duels.", 500, lambda s: s["duel_wins"] >= 10),
    "warlord": ("Warlord", "Win 50 duels.", 1500, lambda s: s["duel_wins"] >= 50),
    "contender": ("Contender", "Reach 1,200 duel rating.", 500, lambda s: s["duel_rating"] >= 1200),
    "master": ("Master", "Reach 1,400 duel rating.", 1500, lambda s: s["duel_rating"] >= 1400),
}


def evaluate(stats):
    """Return the ids of every achievement whose condition is met for these stats."""
    return [aid for aid, (_name, _desc, _reward, condition) in ACHIEVEMENTS.items() if condition(stats)]
