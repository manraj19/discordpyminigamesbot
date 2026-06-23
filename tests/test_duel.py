"""Tests for the duel engine: combat, stat aggregation, AI, and ELO."""

import pytest

from bot.games.duel import (
    aggregate_stats,
    ai_choose,
    available_moves,
    can_rank,
    elo_update,
    level_for_xp,
    make_combatant,
    new_duel,
    step,
)

FULL = ["focus", "guard", "heavy", "bleed"]


def _duel(loadout_a=FULL, loadout_b=FULL, **stat_overrides):
    stats = {"max_hp": 100, "max_energy": 6, "attack": 0, "defense": 0}
    stats.update(stat_overrides)
    a = make_combatant("A", dict(stats), loadout_a)
    b = make_combatant("B", dict(stats), loadout_b)
    return new_duel(a, b)


def test_strike_damage_scales_with_attack_and_defense():
    s = _duel(attack=5)
    s, _, _ = step(s, "strike")  # 8 base + 5 attack = 13, B defense 0
    assert s.fighters[1].hp == 100 - 13


def test_defense_reduces_damage():
    a = make_combatant("A", {"max_hp": 100, "max_energy": 6, "attack": 0, "defense": 0}, FULL)
    b = make_combatant("B", {"max_hp": 100, "max_energy": 6, "attack": 0, "defense": 4}, FULL)
    s = new_duel(a, b)
    s, _, _ = step(s, "strike")  # 8 base - 4 defense = 4
    assert s.fighters[1].hp == 100 - 4


def test_only_kit_moves_are_legal():
    s = _duel(loadout_a=["guard"])  # A has guard but not heavy
    with pytest.raises(ValueError):
        step(s, "heavy")
    # strike is always allowed even when not slotted
    s, _, _ = step(s, "strike")
    assert s.fighters[1].hp < 100


def test_guard_then_strike_is_absorbed():
    s = _duel()
    s, _, _ = step(s, "guard")  # A shields 22, B's turn
    s, _, _ = step(s, "strike")  # B hits 8, fully absorbed
    assert s.fighters[0].hp == 100
    assert s.fighters[0].shield == 22 - 8


def test_stun_makes_target_skip_giving_attacker_a_second_move():
    s = _duel(loadout_a=["concuss"], loadout_b=FULL)
    s.fighters[0].energy = 4
    s, log, winner = step(s, "concuss")  # damage + stun B; B skips, back to A
    assert winner is None
    assert s.active == 0  # A is up again
    assert any("stunned" in line for line in log)


def test_bleed_ticks_on_targets_turn():
    s = _duel()
    s.fighters[0].energy = 2
    s, _, _ = step(s, "bleed")  # 6 direct then 5 bleed on B's turn start
    assert s.fighters[1].hp == 100 - 6 - 5


def test_reducing_hp_to_zero_wins():
    s = _duel()
    s.fighters[1].hp = 8
    s, _, winner = step(s, "strike")
    assert winner is s.fighters[0]


def test_available_moves_respects_energy():
    s = _duel()
    s.fighters[0].energy = 0
    moves = available_moves(s)
    assert "strike" in moves and "focus" in moves  # free moves
    assert "heavy" not in moves  # costs 3


def test_ai_picks_a_legal_move():
    s = _duel()
    assert ai_choose(s) in available_moves(s)


def test_aggregate_stats_adds_gear_and_levels():
    base = aggregate_stats(1)
    assert base == {"max_hp": 100, "max_energy": 6, "attack": 0, "defense": 0}
    geared = aggregate_stats(3, weapon="steel_sword", armor="chainmail", accessory="power_band")
    assert geared["attack"] == 7
    assert geared["defense"] == 4
    assert geared["max_hp"] == 100 + 2 * 8 + 25  # level 3 + chainmail
    assert geared["max_energy"] == 6 + 1


def test_level_for_xp():
    assert level_for_xp(0) == 1
    assert level_for_xp(250) == 3


def test_elo_update_and_gap_gate():
    new_w, new_l = elo_update(1000, 1000)
    assert new_w == 1016 and new_l == 984  # K=32, even match
    assert can_rank(1000, 1300) is True
    assert can_rank(1000, 1500) is False  # gap > 400
