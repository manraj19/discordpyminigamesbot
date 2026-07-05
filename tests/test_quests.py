"""Tests for the quest pool seeding and the QuestService progress/credit logic."""

import datetime
import os
import tempfile

from bot.games.quests import (
    DAILY_BONUS_COINS,
    DAILY_BONUS_TEXT,
    DAILY_BONUS_XP,
    DAILY_COUNT,
    DAILY_POOL,
    WEEKLY_COUNT,
    assign,
    next_reset,
    period_key,
)
from bot.services.quests import QuestService

DAY = datetime.date(2026, 7, 5)


def _fresh_service():
    return QuestService(os.path.join(tempfile.mkdtemp(), "q.db"))


# --- pure pool / seeding ---
def test_assignment_is_deterministic_per_user_and_period():
    key = period_key("daily", DAY)
    first = assign(1, "daily", key)
    assert assign(1, "daily", key) == first  # same seed, same draw
    assert len(first) == DAILY_COUNT
    assert len({q.id for q in first}) == DAILY_COUNT  # no duplicates


def test_assignment_varies_by_user_and_key():
    key = period_key("daily", DAY)
    other_user = assign(2, "daily", key)
    other_day = assign(1, "daily", period_key("daily", DAY + datetime.timedelta(days=1)))
    mine = assign(1, "daily", key)
    # not a guarantee for every pair, but these seeds differ in the current pool
    assert mine != other_user or mine != other_day


def test_weekly_key_is_iso_week_and_count():
    assert period_key("weekly", DAY) == "2026-W27"
    assert len(assign(1, "weekly", period_key("weekly", DAY))) == WEEKLY_COUNT


def test_next_reset_daily_is_next_midnight():
    now = datetime.datetime(2026, 7, 5, 15, 30, tzinfo=datetime.timezone.utc)
    assert next_reset("daily", now) == datetime.datetime(2026, 7, 6, tzinfo=datetime.timezone.utc)
    # 2026-07-05 is a Sunday, so the ISO week rolls over the next day
    assert next_reset("weekly", now) == datetime.datetime(2026, 7, 6, tzinfo=datetime.timezone.utc)


# --- persistence / crediting ---
def test_progress_completes_and_credits_once():
    q = _fresh_service()
    try:
        # a user whose daily draw contains play_3 (find one deterministically)
        user = next(
            u for u in range(1, 500) if "play_3" in {x.id for x in assign(u, "daily", period_key("daily", DAY))}
        )
        target = next(x for x in DAILY_POOL if x.id == "play_3").target
        completed = q.progress(user, "game_play", target, day=DAY)
        assert any(text == "Play 3 games" for text, _c, _x in completed)
        # already claimed: a second event pays nothing more
        assert all(text != "Play 3 games" for text, _c, _x in q.progress(user, "game_play", target, day=DAY))
    finally:
        q.close()


def test_partial_progress_does_not_complete():
    q = _fresh_service()
    try:
        user = next(
            u for u in range(1, 500) if "play_5" in {x.id for x in assign(u, "daily", period_key("daily", DAY))}
        )
        completed = q.progress(user, "game_play", 1, day=DAY)  # play_5 needs 5
        assert all(text != "Play 5 games" for text, _c, _x in completed)
        board = q.board(user, now=datetime.datetime(2026, 7, 5, 12, tzinfo=datetime.timezone.utc))
        prog = next(p for quest, p, _claimed in board["daily"] if quest.id == "play_5")
        assert prog == 1  # partial progress persisted
    finally:
        q.close()


def test_all_dailies_bonus_pays_once():
    q = _fresh_service()
    try:
        user = 1
        dailies = assign(user, "daily", period_key("daily", DAY))
        completed = []
        # drive each daily to completion by feeding its own event kind and target
        for quest in dailies:
            completed += q.progress(user, quest.kind, quest.target, day=DAY)
        texts = [text for text, _c, _x in completed]
        assert texts.count(DAILY_BONUS_TEXT) == 1  # bonus exactly once
        bonus = next((c, x) for text, c, x in completed if text == DAILY_BONUS_TEXT)
        assert bonus == (DAILY_BONUS_COINS, DAILY_BONUS_XP)
        # no further bonus on later events
        more = q.progress(user, dailies[0].kind, dailies[0].target, day=DAY)
        assert all(text != DAILY_BONUS_TEXT for text, _c, _x in more)
    finally:
        q.close()
