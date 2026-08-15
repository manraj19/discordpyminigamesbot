"""Tests for Phase C: cooldowns, momentum, the new abilities, gear enhancement,
the arena tower, and ranked tuning."""

import os
import tempfile

import pytest

from bot.games.duel import (
    ARENA_ARCHETYPES,
    ARENA_BOSS_BONUS,
    MOMENTUM_MAX,
    RATING_FLOOR,
    aggregate_stats,
    ai_choose,
    arena_opponent,
    arena_reward,
    available_moves,
    elo_update,
    enhance_bonus,
    enhance_cost,
    make_combatant,
    new_duel,
    ranked_k,
    step,
)
from bot.services.duel import DuelService

BASE = {"max_hp": 100, "max_energy": 6, "attack": 0, "defense": 0}


def _duel(loadout_a, loadout_b=("focus", "guard", "heavy", "bleed"), **overrides_a):
    stats_a = dict(BASE)
    stats_a.update(overrides_a)
    a = make_combatant("A", stats_a, list(loadout_a))
    b = make_combatant("B", dict(BASE), list(loadout_b))
    return new_duel(a, b)


def _db():
    return os.path.join(tempfile.mkdtemp(), "c.db")


# --- C1: cooldowns ---
def test_cooldown_blocks_then_ticks_down():
    s = _duel(["guard", "focus"])
    step(s, "guard")  # A guards, CD 2 starts
    step(s, "strike")  # B
    # A's turn: cooldown ticked 2 -> 1, still blocked
    assert "guard" not in available_moves(s)
    with pytest.raises(ValueError):
        step(s, "guard")
    step(s, "strike")  # A does something else
    step(s, "strike")  # B
    # A's turn: cooldown ticked 1 -> 0, usable again
    assert "guard" in available_moves(s)


# --- C2: momentum ---
def test_momentum_ramps_damage():
    s = _duel(["focus"])
    step(s, "strike")  # A: 8 damage, gains a stack
    assert s.fighters[0].momentum == 1
    step(s, "focus")  # B passes
    step(s, "strike")  # A: 8 + 2 (one stack)
    assert s.fighters[1].hp == 100 - 8 - 10
    assert s.fighters[0].momentum == 2


def test_momentum_caps_and_resets_on_turtling():
    s = _duel(["guard", "focus"])
    s.fighters[0].momentum = MOMENTUM_MAX
    step(s, "strike")  # dealing damage at the cap stays at the cap
    assert s.fighters[0].momentum == MOMENTUM_MAX
    step(s, "focus")  # B
    step(s, "guard")  # turtling resets A's momentum
    assert s.fighters[0].momentum == 0


def test_momentum_locket_keeps_one_stack():
    s = _duel(["guard", "focus"])
    s.fighters[0].keep_momentum = True
    s.fighters[0].momentum = 4
    step(s, "guard")
    assert s.fighters[0].momentum == 1


# --- C3: new abilities ---
def test_twinstrike_hits_twice():
    s = _duel(["twinstrike"])
    step(s, "twinstrike")
    assert s.fighters[1].hp == 100 - 2 * 7
    assert s.fighters[0].momentum == 1  # one stack per ability, not per hit


def test_shatter_destroys_shield_then_hits():
    s = _duel(["shatter"])
    s.fighters[1].shield = 20
    step(s, "shatter")
    assert s.fighters[1].shield == 0
    assert s.fighters[1].hp == 100 - 12


def test_ward_cleanses_own_afflictions():
    s = _duel(["ward"])
    s.fighters[0].bleed, s.fighters[0].poison, s.fighters[0].weaken = 2, 1, 2
    step(s, "ward")
    a = s.fighters[0]
    assert a.bleed == 0 and a.poison == 0 and a.weaken == 0
    assert a.shield == 8


def test_rupture_consumes_dots_for_burst():
    s = _duel(["rupture"])
    s.fighters[1].bleed, s.fighters[1].poison = 2, 2
    s.fighters[1].shield = 50  # like DoTs, rupture ignores shield
    step(s, "rupture")
    b = s.fighters[1]
    assert b.hp == 100 - 4 * 7
    assert b.bleed == 0 and b.poison == 0
    assert b.shield == 50


def test_rupture_without_wounds_does_nothing():
    s = _duel(["rupture"])
    step(s, "rupture")
    assert s.fighters[1].hp == 100
    assert s.fighters[0].momentum == 0  # no damage, no stack


def test_adrenaline_only_below_half_hp():
    s = _duel(["adrenaline"])
    assert "adrenaline" not in available_moves(s)  # full HP
    with pytest.raises(ValueError):
        step(s, "adrenaline")
    s.fighters[0].hp = 40
    assert "adrenaline" in available_moves(s)
    step(s, "adrenaline")  # cost 1, +2 energy, +8 heal
    assert s.fighters[0].hp == 48
    assert s.fighters[0].energy == 3 - 1 + 2


def test_riposte_counters_an_absorbed_hit_once():
    s = _duel(["focus"], ["riposte"])
    step(s, "focus")  # A passes; B's turn
    step(s, "riposte")  # B shields 12 and readies
    step(s, "strike")  # A's 8 is absorbed, riposte hits back for 12
    assert s.fighters[0].hp == 100 - 12
    assert s.fighters[1].riposte_ready is False
    assert s.fighters[1].hp == 100


def test_riposte_window_closes_at_own_turn():
    s = _duel(["focus"], ["riposte", "focus"])
    step(s, "focus")
    step(s, "riposte")
    step(s, "focus")  # A doesn't attack; B's turn starts, window closes
    assert s.fighters[1].riposte_ready is False
    step(s, "focus")  # B passes back to A
    step(s, "strike")  # absorbed by leftover shield but no counter
    assert s.fighters[0].hp == 100


def test_riposte_can_fell_the_attacker():
    s = _duel(["focus"], ["riposte"])
    s.fighters[0].hp = 10
    step(s, "focus")
    step(s, "riposte")
    _, _, winner = step(s, "strike")  # counter kills A mid-swing
    assert winner is s.fighters[1]


# --- C4: gear and enhancement ---
def test_enhance_cost_ladder():
    costs = [enhance_cost(level) for level in range(5)]
    assert costs == [300, 600, 1200, 2400, 4800]
    assert sum(costs) == 9300


def test_enhance_bonus_by_slot():
    assert enhance_bonus("weapon", 3) == {"attack": 3}
    assert enhance_bonus("armor", 2) == {"defense": 2}
    assert enhance_bonus("accessory", 5) == {"max_hp": 20}


def test_aggregate_stats_with_enhancements_and_passives():
    stats = aggregate_stats(1, weapon="berserker_axe", accessory="regen_ring", gear_levels={"berserker_axe": 3})
    assert stats["attack"] == 16 + 3
    assert stats["max_hp"] == 100 - 15
    assert stats["regen"] == 2
    locket = aggregate_stats(1, accessory="momentum_locket")
    assert locket["keep_momentum"] is True


def test_regen_ring_heals_at_turn_start():
    s = _duel(["focus"], regen=2)
    step(s, "focus")  # A passes
    step(s, "strike")  # B hits A for 8; A's turn starts and regens 2
    assert s.fighters[0].hp == 100 - 8 + 2


# --- C5: arena tower ---
def test_arena_opponent_scales_and_rotates():
    name1, stats1, kit1, boss1 = arena_opponent(1, player_level=1)
    assert not boss1
    assert (name1, kit1) == ARENA_ARCHETYPES[0]
    assert stats1["attack"] == 1
    assert stats1["max_hp"] == round(100 * 1.05)
    _, stats3, kit3, _ = arena_opponent(3, player_level=1)
    assert stats3["attack"] == 3
    assert kit3 == ARENA_ARCHETYPES[2][1]


def test_arena_bosses_every_fifth_floor():
    name, _, _, boss = arena_opponent(5, player_level=1)
    assert boss and name == "Ironjaw"
    assert arena_reward(5, True) == 20 + 50 + ARENA_BOSS_BONUS
    assert arena_reward(3, False) == 50


def test_ai_plays_legal_moves_with_every_archetype():
    for _name, kit in ARENA_ARCHETYPES:
        s = new_duel(make_combatant("AI", dict(BASE), list(kit)), make_combatant("P", dict(BASE), list(kit)))
        for _ in range(30):
            choice = ai_choose(s)
            assert choice in available_moves(s)
            _, _, winner = step(s, choice)
            if winner is not None:
                break


# --- C6: ranked tuning ---
def test_ranked_k_placement_then_settled():
    assert ranked_k(0) == 40
    assert ranked_k(9) == 40
    assert ranked_k(10) == 24


def test_elo_per_player_k_and_floor():
    new_w, new_l = elo_update(1000, 1000, k=40, k_loser=24)
    assert new_w == 1020 and new_l == 988
    _, floored = elo_update(1000, 805)
    assert floored == RATING_FLOOR


# --- service persistence ---
def test_gear_enhance_persists():
    d = DuelService(_db())
    try:
        d.get_or_create(1, "A")
        d.grant_gear(1, "rusty_sword")
        assert d.gear_level(1, "rusty_sword") == 0
        assert d.enhance_gear(1, "rusty_sword") == 1
        assert d.gear_levels(1) == {"rusty_sword": 1}
        assert d.max_gear_level(1) == 1
    finally:
        d.close()


def test_arena_attempts_cap_and_daily_reset():
    d = DuelService(_db())
    try:
        d.get_or_create(1, "A")
        for i in range(5):
            ok, left = d.use_arena_attempt(1, 5, today="2026-07-05")
            assert ok and left == 4 - i
        ok, _ = d.use_arena_attempt(1, 5, today="2026-07-05")
        assert not ok  # capped for the day
        ok, left = d.use_arena_attempt(1, 5, today="2026-07-06")
        assert ok and left == 4  # a new day resets the counter
    finally:
        d.close()


def test_advance_arena_floor():
    d = DuelService(_db())
    try:
        d.get_or_create(1, "A")
        assert d.advance_arena_floor(1) == 1
        assert d.advance_arena_floor(1) == 2
        assert d.get(1)["arena_floor"] == 2
    finally:
        d.close()


def test_apply_match_ranked_counters():
    d = DuelService(_db())
    try:
        d.get_or_create(1, "A")
        d.apply_match(1, "A", True, 10, ranked=True)
        d.apply_match(1, "A", True, 10, ranked=True)
        rec = d.get(1)
        assert rec["ranked_games"] == 2 and rec["ranked_streak"] == 2
        d.apply_match(1, "A", False, 5, ranked=True)
        rec = d.get(1)
        assert rec["ranked_games"] == 3 and rec["ranked_streak"] == 0
        d.apply_match(1, "A", True, 10)  # casual: counters untouched
        assert d.get(1)["ranked_games"] == 3
    finally:
        d.close()
