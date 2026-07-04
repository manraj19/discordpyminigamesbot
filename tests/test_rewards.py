"""Tests for the unified reward pipeline and achievement rewards (Phase A)."""

from bot.core.rewards import RewardResult, progress_bar
from bot.games.achievements import ACHIEVEMENTS, evaluate


def test_progress_bar():
    assert progress_bar(0, 100, width=10) == "▱" * 10
    assert progress_bar(100, 100, width=10) == "▰" * 10
    assert progress_bar(50, 100, width=10) == "▰▰▰▰▰▱▱▱▱▱"
    assert progress_bar(5, 0, width=4) == "▱▱▱▱"  # zero total is safe, not a crash


def test_reward_line_empty_when_nothing_earned():
    assert RewardResult().line() == ""


def test_reward_line_coins_only():
    line = RewardResult(coins=15).line()
    assert "15" in line and "MiniCoins" in line
    assert "·" not in line  # single part, no separator


def test_reward_line_combines_every_part():
    line = RewardResult(coins=15, xp=5, level_up=6, first_win_bonus=40, new_achievements=[("Gladiator", 500)]).line()
    for token in ("MiniCoins", "XP", "Level 6", "First win", "Gladiator"):
        assert token in line
    assert line.count("·") == 4  # five parts, four separators


def test_every_achievement_is_a_rewarded_4_tuple():
    for _aid, entry in ACHIEVEMENTS.items():
        name, desc, reward, cond = entry
        assert name and desc
        assert isinstance(reward, int) and reward > 0
        assert callable(cond)


def test_achievement_thresholds():
    base = {"total_score": 0, "coins": 0, "streak": 0, "duel_wins": 0, "duel_rating": 1000}
    assert evaluate(base) == []
    maxed = {"total_score": 10000, "coins": 50000, "streak": 100, "duel_wins": 50, "duel_rating": 1400}
    earned = set(evaluate(maxed))
    # the original tier plus the new higher tiers all unlock
    assert {"first_win", "rich", "loaded", "dedicated", "duelist", "gladiator", "contender"} <= earned
    assert {"prodigy", "tycoon", "centurion", "warlord", "master"} <= earned
