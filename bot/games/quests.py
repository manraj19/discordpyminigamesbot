"""Pure quest pool and per-user assignment. No discord, no DB.

Quests are drawn per user per period, not stored: seeding
``random.Random(f"{user_id}:{period_key}")`` and sampling the pool gives every
player a stable set for the day (or week) that anyone can recompute. Only
progress lives in the database (``QuestService``).

Every quest is a plain integer counter against a target, so a single event
(``game_play``, ``game_win``, ``coins_earned``, ``duel_win``, ``wager``) advances
whatever matching quests are active. Nothing here needs richer per-game state.
"""

import datetime
import random
from dataclasses import dataclass

DAILY_COUNT = 3  # dailies drawn per user per day
WEEKLY_COUNT = 2  # weeklies drawn per user per week

# Finishing all of the day's dailies pays this on top of each quest's own reward.
DAILY_BONUS_TEXT = "All dailies done"
DAILY_BONUS_COINS = 100
DAILY_BONUS_XP = 30
DAILY_BONUS_ID = "_daily_all"  # synthetic quest id used to mark the bonus as paid


@dataclass(frozen=True)
class Quest:
    id: str
    text: str
    kind: str  # game_play | game_win | coins_earned | duel_win | wager
    target: int
    coins: int
    xp: int = 0


# All progress is a clean counter, so quests stay farm-resistant only through
# their fixed rewards (by design, per the plan). Tune these against ;usage data.
DAILY_POOL = [
    Quest("play_3", "Play 3 games", "game_play", 3, coins=60),
    Quest("play_5", "Play 5 games", "game_play", 5, coins=80),
    Quest("win_2", "Win 2 games", "game_win", 2, coins=50, xp=20),
    Quest("win_4", "Win 4 games", "game_win", 4, coins=90, xp=30),
    Quest("earn_150", "Earn 150 MiniCoins from games", "coins_earned", 150, coins=60),
    Quest("duel_win_1", "Win a duel or arena fight", "duel_win", 1, coins=70, xp=25),
    Quest("wager_100", "Wager 100 MiniCoins on gambling", "wager", 100, coins=40),
]

WEEKLY_POOL = [
    Quest("win_10", "Win 10 games", "game_win", 10, coins=300, xp=100),
    Quest("play_25", "Play 25 games", "game_play", 25, coins=250, xp=80),
    Quest("duels_5", "Win 5 duels or arena fights", "duel_win", 5, coins=400, xp=150),
    Quest("earn_1000", "Earn 1,000 MiniCoins from games", "coins_earned", 1000, coins=300, xp=100),
    Quest("wager_1000", "Wager 1,000 MiniCoins on gambling", "wager", 1000, coins=250, xp=80),
]

_POOLS = {"daily": (DAILY_POOL, DAILY_COUNT), "weekly": (WEEKLY_POOL, WEEKLY_COUNT)}


def period_key(period, day):
    """Stable key for the day's dailies or the week's weeklies (a ``date``).

    Daily is the ISO date; weekly is the ISO year and week, so it rolls over on
    Monday the same way ``isocalendar`` does."""
    if period == "daily":
        return day.isoformat()
    year, week, _weekday = day.isocalendar()
    return f"{year}-W{week:02d}"


def assign(user_id, period, key):
    """The quests this user holds for one period, drawn deterministically from
    the pool. Same ``(user_id, key)`` always gives the same set."""
    pool, count = _POOLS[period]
    rng = random.Random(f"{user_id}:{key}")
    return rng.sample(pool, count)


def next_reset(period, now):
    """When the current period ends, as a UTC ``datetime`` (``now`` is UTC).

    Dailies reset at the next midnight; weeklies at the next Monday midnight."""
    midnight = datetime.datetime.combine(now.date(), datetime.time(), tzinfo=datetime.timezone.utc)
    if period == "daily":
        return midnight + datetime.timedelta(days=1)
    return midnight + datetime.timedelta(days=7 - now.weekday())
