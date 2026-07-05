"""Tests for the daily-claim streak/reward logic and the EconomyService."""

import datetime
import os
import tempfile

from bot.services.economy import (
    BASE_DAILY,
    STREAK_BONUS,
    STREAK_CAP_DAYS,
    STREAKSHIELD_PRICE,
    TITLES,
    WIN_COINS,
    EconomyService,
    daily_outcome,
    payout,
    streak_milestone,
)


def _fresh_service():
    db = os.path.join(tempfile.mkdtemp(), "econ.db")
    return EconomyService(db)


DAY = datetime.date(2026, 6, 19)


def test_first_claim_starts_streak_at_one():
    claimed, streak, reward = daily_outcome(None, DAY, 0)
    assert claimed and streak == 1 and reward == BASE_DAILY


def test_consecutive_day_grows_streak_and_reward():
    claimed, streak, reward = daily_outcome(DAY - datetime.timedelta(days=1), DAY, 3)
    assert claimed and streak == 4 and reward == BASE_DAILY + 3 * STREAK_BONUS


def test_gap_resets_streak():
    claimed, streak, reward = daily_outcome(DAY - datetime.timedelta(days=3), DAY, 9)
    assert claimed and streak == 1 and reward == BASE_DAILY


def test_same_day_not_claimable():
    claimed, streak, reward = daily_outcome(DAY, DAY, 5)
    assert not claimed and streak == 5 and reward == 0


def test_reward_caps_after_a_week():
    claimed, streak, reward = daily_outcome(DAY - datetime.timedelta(days=1), DAY, 20)
    assert claimed and reward == BASE_DAILY + STREAK_CAP_DAYS * STREAK_BONUS


def test_payout_win_games_flat_score_games_scaled():
    assert payout("wordguess", 1) == WIN_COINS  # win-based game
    assert payout("guessnumber", 1) == WIN_COINS
    assert payout("dino", 10) == 30  # 3 per point
    assert payout("mathematics", 4) == 20  # 5 per point
    assert payout("dino", 0) == 0  # no score, no coins


def test_spend_only_when_affordable():
    econ = _fresh_service()
    try:
        econ.add_coins(1, "u", 100)
        assert econ.spend(1, 150) is False  # can't overspend
        assert econ.balance(1)[0] == 100  # balance untouched
        assert econ.spend(1, 60) is True
        assert econ.balance(1)[0] == 40
    finally:
        econ.close()


def test_buy_title_flow():
    econ = _fresh_service()
    try:
        item = "novice"
        price = TITLES[item][1]
        # too poor to start
        assert econ.buy_title(2, "u", item) == "poor"
        econ.add_coins(2, "u", price)
        # first buy: charged, owned, equipped
        assert econ.buy_title(2, "u", item) == "bought"
        assert econ.balance(2)[0] == 0
        assert econ.equipped_title(2) == item
        assert item in econ.owned_titles(2)
        # re-buying something owned just re-equips, free
        assert econ.buy_title(2, "u", item) == "equipped"
        assert econ.balance(2)[0] == 0
        assert econ.buy_title(2, "u", "does-not-exist") == "unknown"
    finally:
        econ.close()


def test_streak_milestone_rewards():
    assert streak_milestone(6) == (0, None)  # non-milestone day
    assert streak_milestone(7) == (250, None)  # coins, no title
    assert streak_milestone(30) == (1000, "committed")
    assert streak_milestone(100) == (2500, "ironwilled")


def test_buy_streakshield_flow():
    econ = _fresh_service()
    try:
        assert econ.buy_streakshield(1, "u") == "poor"  # can't afford
        econ.add_coins(1, "u", STREAKSHIELD_PRICE)
        assert econ.buy_streakshield(1, "u") == "bought"
        assert econ.owns(1, "streakshield")
        assert econ.buy_streakshield(1, "u") == "have"  # only one at a time
    finally:
        econ.close()


def test_streak_shield_saves_a_single_missed_day():
    econ = _fresh_service()
    try:
        d1 = datetime.date(2026, 7, 1)
        _c, _r, streak, _co, _e = econ.claim_daily(1, "u", today=d1)
        assert streak == 1
        econ.add_coins(1, "u", STREAKSHIELD_PRICE)
        econ.buy_streakshield(1, "u")
        # claim two days later: one missed day, the shield rescues the streak
        d3 = d1 + datetime.timedelta(days=2)
        claimed, _r, streak, _co, extras = econ.claim_daily(1, "u", today=d3)
        assert claimed and streak == 2 and extras["shield_saved"]
        assert not econ.owns(1, "streakshield")  # consumed
    finally:
        econ.close()


def test_streak_shield_only_covers_one_missed_day():
    econ = _fresh_service()
    try:
        d1 = datetime.date(2026, 7, 1)
        econ.claim_daily(1, "u", today=d1)
        econ.add_coins(1, "u", STREAKSHIELD_PRICE)
        econ.buy_streakshield(1, "u")
        d4 = d1 + datetime.timedelta(days=3)  # two missed days is too big a gap
        claimed, _r, streak, _co, extras = econ.claim_daily(1, "u", today=d4)
        assert claimed and streak == 1 and not extras["shield_saved"]
        assert econ.owns(1, "streakshield")  # not consumed
    finally:
        econ.close()


def test_streak_milestone_grants_and_equips_title():
    econ = _fresh_service()
    try:
        start = datetime.date(2026, 7, 1)
        extras = {}
        for i in range(30):
            *_head, extras = econ.claim_daily(1, "u", today=start + datetime.timedelta(days=i))
        assert extras["milestone_coins"] == 1000
        assert extras["milestone_title"] == "The Committed"
        assert econ.equipped_title(1) == "committed"  # auto-equipped on grant
    finally:
        econ.close()


def test_service_claim_then_second_claim_is_blocked():
    db = os.path.join(tempfile.mkdtemp(), "econ.db")
    econ = EconomyService(db)
    try:
        claimed, reward, streak, coins, _extras = econ.claim_daily(7, "tester")
        assert claimed and reward == BASE_DAILY and streak == 1 and coins == BASE_DAILY
        # second claim the same day is refused and the balance is unchanged
        claimed2, reward2, _streak2, coins2, _extras2 = econ.claim_daily(7, "tester")
        assert not claimed2 and reward2 == 0 and coins2 == BASE_DAILY
        assert econ.balance(7) == (BASE_DAILY, 1)
    finally:
        econ.close()
