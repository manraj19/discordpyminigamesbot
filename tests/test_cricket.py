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
    # overs/5 cap: 20 overs -> max 4 each (24 balls). Check it holds across many matches.
    for seed in range(200):
        *_, bowling = _run(20, 4, seed)
        assert max(balls for balls, _runs in bowling.values()) <= 4 * 6


def test_overs_bowled_match_innings_length():
    # A completed innings (nobody all out) bowls exactly `overs` overs total.
    for seed in range(50):
        _runs, wickets, *_, _balls, bowling = _run(10, 2, seed)
        assert wickets <= 10
        if wickets < 10:
            assert sum(balls for balls, _r in bowling.values()) == 10 * 6


def test_innings_is_consistent():
    runs, wickets, scores, wkts, events, *_, bowling = _run(20, 4, 1)
    assert runs == sum(scores.values())  # total runs == sum of individual scores
    assert sum(wkts.values()) <= wickets  # bowler wickets can't exceed total (run-outs aren't credited)
    assert runs == sum(conceded for _b, conceded in bowling.values())  # every run is charged to a bowler
    assert events  # commentary was produced


def test_bowling_figures_in_summary():
    from bot.games.cricket import get_top_performers

    runs, _w, scores, wkts, *_, balls_faced, bowling = _run(10, 2, 7)
    _bats, bowlers = get_top_performers(scores, wkts, balls_faced, bowling)
    assert bowlers, "someone bowled"
    for _player, overs_str, conceded, wickets in bowlers:
        assert "." in overs_str  # overs shown in cricket notation, e.g. 2.0
        assert conceded >= 0 and wickets >= 0
    # best wicket-takers first
    taken = [row[3] for row in bowlers]
    assert taken == sorted(taken, reverse=True)
