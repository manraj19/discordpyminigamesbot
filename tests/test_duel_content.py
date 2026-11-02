"""The second batch of duel abilities and gear, and the limits the catalogue must fit."""

from types import SimpleNamespace

from bot.cogs.duel import Duel
from bot.games.duel import (
    ABILITIES,
    GEAR,
    LOADOUT_SIZE,
    SECOND_MOVER_ENERGY,
    START_ENERGY,
    aggregate_stats,
    make_combatant,
    new_duel,
    step,
)
from bot.views.duel import LoadoutSelect, _status_line, rules_embed

BASE = {"max_hp": 100, "max_energy": 6, "attack": 0, "defense": 0}


def _duel(loadout, gear=None, foe_gear=None):
    a = make_combatant("A", {**BASE, **(gear or {})}, list(loadout))
    b = make_combatant("B", {**BASE, **(foe_gear or {})}, ["focus", "guard", "heavy", "bleed"])
    a.energy = b.energy = 6
    return new_duel(a, b)


def test_second_mover_gets_the_catch_up_energy():
    a = make_combatant("A", BASE, [])
    b = make_combatant("B", BASE, [])
    new_duel(a, b, 1, SECOND_MOVER_ENERGY)
    assert b.energy == START_ENERGY  # goes first
    assert a.energy == START_ENERGY + SECOND_MOVER_ENERGY


def test_pierce_skips_defense_and_shield():
    s = _duel(["pierce"], foe_gear={"defense": 9})
    s.fighters[1].shield = 30
    step(s, "pierce")
    assert s.fighters[1].hp == 100 - 14
    assert s.fighters[1].shield == 30


def test_recoil_hurts_the_user_but_never_kills():
    s = _duel(["reckless"])
    step(s, "reckless")
    assert s.fighters[1].hp == 100 - 20
    assert s.fighters[0].hp == 100 - 6
    s = _duel(["reckless"])
    s.fighters[0].hp = 3
    step(s, "reckless")
    assert s.fighters[0].hp == 1


def test_recoil_cant_bring_back_someone_the_thorns_killed():
    s = _duel(["reckless"], foe_gear={"thorns": 4})
    s.fighters[0].hp = 4
    _, _, winner = step(s, "reckless")
    assert s.fighters[0].hp == 0
    assert winner is s.fighters[1]


def test_leech_cant_heal_back_from_a_killing_thorn():
    s = _duel(["twinstrike"], gear={"leech": 100}, foe_gear={"thorns": 50})
    s.fighters[0].hp = 41  # the first hit heals 9 to 50, then the thorns leave 0
    _, _, winner = step(s, "twinstrike")
    assert winner is s.fighters[1]
    assert s.fighters[1].hp == 100 - 9  # the second hit never came


def test_sidestep_dodges_one_hit_and_breaks_momentum():
    s = _duel(["sidestep"])
    step(s, "sidestep")
    s.fighters[1].momentum = 4
    step(s, "heavy")
    assert s.fighters[0].hp == 100
    assert s.fighters[1].momentum == 0


def test_a_dodged_hit_brings_no_effects_with_it():
    s = _duel(["sidestep"])
    s.fighters[1].loadout = ["concuss"]
    step(s, "sidestep")
    step(s, "concuss")
    assert s.active == 0  # A's turn comes round, where a landed stun would skip it
    assert s.fighters[1].energy == 6 - 4  # the move is still paid for
    assert s.fighters[1].cooldowns["concuss"] > 0
    s = _duel(["sidestep"])
    step(s, "sidestep")
    step(s, "bleed")
    assert s.fighters[0].bleed == 0


def test_a_second_hit_gets_past_a_sidestep():
    s = _duel(["sidestep"])
    s.fighters[1].loadout = ["twinstrike"]
    step(s, "sidestep")
    step(s, "twinstrike")
    assert s.fighters[0].hp == 100 - 4
    assert s.fighters[1].momentum == 1


def test_sidestep_ends_at_the_users_next_turn():
    s = _duel(["sidestep"])
    step(s, "sidestep")
    step(s, "focus")  # nothing tested the dodge, so it's gone when A's turn comes round
    assert s.fighters[0].evading is False


def test_unleash_spends_momentum_for_burst():
    s = _duel(["unleash"])
    s.fighters[0].momentum = 5
    step(s, "unleash")
    assert s.fighters[1].hp == 100 - (6 + 2 * 5 + 4 * 5)
    assert s.fighters[0].momentum == 0


def test_siphon_drains_energy_down_to_zero():
    s = _duel(["siphon"])
    s.fighters[1].energy = 1
    step(s, "siphon")
    # B lost their 1 energy, then regained 1 at the start of their turn.
    assert s.fighters[1].energy == 1
    assert s.fighters[1].hp == 100 - 4


def test_expose_adds_to_each_later_hit_and_wears_off():
    s = _duel(["expose"])
    step(s, "expose")
    assert s.fighters[1].hp == 100 - 4  # no bonus on the hit that applies it
    for expected_bonus in (5, 5, 5, 0):
        before = s.fighters[1].hp
        step(s, "focus")  # B
        momentum = s.fighters[0].momentum
        step(s, "strike")  # A
        assert before - s.fighters[1].hp == 8 + 2 * momentum + expected_bonus


def test_ward_clears_exposure():
    s = _duel(["ward"])
    s.fighters[0].exposed = 3
    step(s, "ward")
    assert s.fighters[0].exposed == 0


def test_vengeance_grows_with_missing_hp():
    s = _duel(["vengeance"])
    step(s, "vengeance")
    assert s.fighters[1].hp == 100 - 6  # at full HP it's a weak hit
    s = _duel(["vengeance"])
    s.fighters[0].hp = 20
    step(s, "vengeance")
    assert s.fighters[1].hp == 100 - (6 + 80 // 4)


def test_finisher_range_is_a_share_of_max_hp():
    s = _duel(["finisher"], foe_gear={"max_hp": 300})
    s.fighters[1].hp = 80  # under 30% of 300, though well over 30 HP
    step(s, "finisher")
    assert s.fighters[1].hp == 80 - (18 + 30)


def test_mend_keeps_up_with_max_hp():
    s = _duel(["mend"], gear={"max_hp": 300})
    s.fighters[0].hp = 100
    step(s, "mend")
    assert s.fighters[0].hp == 100 + 16 + 45


def test_focus_keeps_momentum():
    s = _duel(["focus"])
    s.fighters[0].momentum = 3
    step(s, "focus")
    assert s.fighters[0].momentum == 3


def test_leech_heals_a_share_of_each_hit():
    s = _duel(["heavy"], gear={"leech": 25})
    s.fighters[0].hp = 50
    step(s, "heavy")
    assert s.fighters[0].hp == 50 + 22 // 4


def test_thorns_hurt_per_hit_and_can_kill_the_attacker():
    s = _duel(["twinstrike"], foe_gear={"thorns": 4})
    step(s, "twinstrike")
    assert s.fighters[0].hp == 100 - 2 * 4
    s = _duel(["heavy"], foe_gear={"thorns": 4})
    s.fighters[0].hp = 4
    _, _, winner = step(s, "heavy")
    assert winner is s.fighters[1]


def test_armor_pen_only_cancels_defense():
    s = _duel(["heavy"], gear={"armor_pen": 3}, foe_gear={"defense": 2})
    step(s, "heavy")
    assert s.fighters[1].hp == 100 - 22  # 3 pen against 2 defense can't add damage


def test_dot_bonus_extends_wounds():
    s = _duel(["bleed"], gear={"dot_bonus": 1})
    step(s, "bleed")
    # Three turns of bleed plus the bonus, with one already ticked as B's turn began.
    assert s.fighters[1].bleed == 3


def test_last_stand_saves_one_hit_but_not_wounds():
    s = _duel(["heavy"], foe_gear={"last_stand": True})
    s.fighters[1].hp = 5
    _, _, winner = step(s, "heavy")
    assert winner is None and s.fighters[1].hp == 10  # 10% of 100, before the charm is spent
    assert s.fighters[1].last_stand is False
    s = _duel(["focus"], foe_gear={"last_stand": True})
    s.fighters[1].hp = 5
    s.fighters[1].bleed = 2
    _, _, winner = step(s, "focus")  # the bleed ticks at the start of B's turn, and the charm doesn't help
    assert winner is s.fighters[0]


def test_last_stand_covers_a_riposte_or_thorns_on_the_attacker():
    s = _duel(["heavy"], gear={"last_stand": True}, foe_gear={"thorns": 4})
    s.fighters[0].hp = 4
    _, _, winner = step(s, "heavy")
    assert winner is None and s.fighters[0].hp == 10


def test_locket_never_grants_momentum_it_didnt_have():
    s = _duel(["guard"])
    s.fighters[0].keep_momentum = True
    step(s, "guard")
    assert s.fighters[0].momentum == 0


def test_start_of_duel_gear():
    stats = aggregate_stats(1, accessory="war_drum")
    assert make_combatant("A", stats, []).momentum == 3
    stats = aggregate_stats(1, accessory="aegis_pendant")
    assert make_combatant("A", stats, []).shield == 30


def test_juggernaut_costs_max_energy():
    assert aggregate_stats(1, armor="juggernaut_plate")["max_energy"] == 5


def test_status_line_shows_the_new_effects():
    fighter = make_combatant("A", {**BASE, "last_stand": True}, [])
    fighter.exposed, fighter.evading = 2, True
    line = _status_line(fighter)
    assert "🎯2" in line and "💨" in line and "🪶" in line


def test_catalogue_fits_discord():
    """One select lists every owned ability, and buttons can't exceed a row."""
    assert len(ABILITIES) - 1 <= 25  # Strike is never offered, it's always in the kit
    assert 1 + LOADOUT_SIZE <= 5
    LoadoutSelect([a for a in ABILITIES if a != "strike"], ["heavy"])
    assert len(GEAR) <= 25  # autocomplete shows 25 at most, so past this some items can't be found
    assert all(gear["slot"] in ("weapon", "armor", "accessory") for gear in GEAR.values())


def test_rules_and_shop_fit_in_one_embed():
    duel = SimpleNamespace(owned_gear=lambda _: [], gear_levels=lambda _: {}, unlocked_abilities=lambda _: [])
    shop = Duel._shop_embed(SimpleNamespace(bot=SimpleNamespace(duel=duel)), SimpleNamespace(id=1))
    for embed in (rules_embed(), shop):
        assert len(embed) <= 6000
        assert all(len(field.value) <= 1024 for field in embed.fields)
