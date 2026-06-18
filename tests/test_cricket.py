"""Tests for the cricket innings simulator: the bowler over-cap and that an
innings stays internally consistent (the two-batsmen rewrite)."""

import random

from bot.games.cricket import simulate_innings

TEAM_A = [f"A{i}" for i in range(11)]
TEAM_B = [f"B{i}" for i in range(11)]


def _run(overs, cap, seed):
    random.seed(seed)
    return simulate_innings(TEAM_A, TEAM_B, overs, cap)


def test_no_bowler_exceeds_cap():
    # overs/5 cap: 20 overs -> max 4 each. Check it holds across many matches.
    for seed in range(200):
        *_, bowler_overs = _run(20, 4, seed)
        assert max(bowler_overs.values()) <= 4


def test_overs_bowled_match_innings_length():
    # A completed innings (nobody all out) bowls exactly `overs` overs total.
    for seed in range(50):
        _runs, wickets, *_, _balls, bowler_overs = _run(10, 2, seed)
        assert wickets <= 10
        if wickets < 10:
            assert sum(bowler_overs.values()) == 10


def test_innings_is_consistent():
    runs, wickets, scores, wkts, events, *_ = _run(20, 4, 1)
    assert runs == sum(scores.values())  # total runs == sum of individual scores
    assert sum(wkts.values()) <= wickets  # bowler wickets can't exceed total (run-outs aren't credited)
    assert events  # commentary was produced
