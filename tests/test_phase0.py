"""Tests for Phase 0: per-server scores, achievements, vote rewards, season reset."""

import datetime
import os
import sqlite3
import tempfile

from bot.games.achievements import evaluate
from bot.services.channel_lock import ChannelLockService
from bot.services.duel import DuelService
from bot.services.economy import VOTE_COOLDOWN_HOURS, VOTE_REWARD, EconomyService
from bot.services.scores import ScoreService


def _db():
    return os.path.join(tempfile.mkdtemp(), "p.db")


def test_scores_are_per_server():
    s = ScoreService(_db())
    s.record_result(1, "u", 5, "dino", guild_id=100)
    s.record_result(1, "u", 9, "dino", guild_id=200)
    assert s.user_score(1, "dino", 100) == 5
    assert s.user_score(1, "dino", 200) == 9
    assert s.top("dino", 100) == [("u", 5)]
    assert s.top("dino", 200) == [("u", 9)]
    assert s.total_user_score(1) == 14  # summed across servers
    s.close()


def test_scores_global_aggregates_across_servers():
    s = ScoreService(_db())
    s.record_result(1, "u", 5, "wordguess", guild_id=100)  # cumulative game
    s.record_result(1, "u", 9, "wordguess", guild_id=200)
    assert s.top("wordguess") == [("u", 14)]  # global default sums across servers
    assert s.user_score(1, "wordguess") == 14
    # best-score game takes the best server result globally
    s.record_result(2, "d", 5, "dino", guild_id=100)
    s.record_result(2, "d", 9, "dino", guild_id=200)
    assert s.top("dino") == [("d", 9)]
    s.close()


def test_scores_legacy_migration():
    db = _db()
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE scores (user_id INTEGER, username TEXT, score INTEGER, game TEXT, PRIMARY KEY (user_id, game))"
    )
    conn.execute("INSERT INTO scores VALUES (1, 'old', 7, 'dino')")
    conn.commit()
    conn.close()
    s = ScoreService(db)  # should migrate the pre-per-server table
    assert s.user_score(1, "dino", 0) == 7  # legacy rows land in bucket 0
    s.close()


def test_achievements_evaluate():
    base = {"total_score": 0, "coins": 0, "streak": 0, "duel_wins": 0, "duel_rating": 1000}
    assert evaluate(base) == []
    maxed = {"total_score": 1, "coins": 10000, "streak": 7, "duel_wins": 10, "duel_rating": 1200}
    earned = set(evaluate(maxed))
    assert {"first_win", "rich", "loaded", "dedicated", "duelist", "gladiator", "contender"} <= earned


def test_achievement_storage():
    e = EconomyService(_db())
    assert not e.has_achievement(1, "rich")
    e.grant_achievement(1, "rich")
    assert e.has_achievement(1, "rich")
    assert e.earned_achievements(1) == ["rich"]
    e.close()


def test_claim_vote_cooldown():
    e = EconomyService(_db())
    now = datetime.datetime(2026, 6, 20, 12, 0, tzinfo=datetime.timezone.utc)
    claimed, reward, _ = e.claim_vote(1, "u", now)
    assert claimed and reward == VOTE_REWARD
    # within the cooldown it's blocked
    blocked, reward2, hours = e.claim_vote(1, "u", now + datetime.timedelta(hours=1))
    assert not blocked and reward2 == 0 and hours >= 1
    # once the cooldown elapses it claims again
    claimed3, _, _ = e.claim_vote(1, "u", now + datetime.timedelta(hours=VOTE_COOLDOWN_HOURS))
    assert claimed3
    e.close()


def test_channel_lock():
    c = ChannelLockService(_db())
    assert not c.is_disabled(123)
    c.disable(123)
    assert c.is_disabled(123)
    assert c.all() == [123]
    c.enable(123)
    assert not c.is_disabled(123)
    c.close()


def test_duel_reset_season():
    d = DuelService(_db())
    d.get_or_create(1, "A")
    d.apply_match(1, "A", True, 25, new_rating=1300, trophies=50)
    champ = d.reset_season()
    assert champ == ("A", 1300)  # pre-reset top is the season champion
    after = d.get(1)
    assert after["rating"] == 1000 and after["trophies"] == 0
    d.close()
