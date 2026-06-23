"""Pure duel system core: deterministic combat, gear/ability catalogues, stat
aggregation, a deterministic AI, and ELO maths. No discord imports.

Duel is the technical, skill-only ranked mode (fight is the random fun one), so
combat has no dice. Depth comes from energy management, status effects, gear, and
ability loadouts. Every number here is a tunable constant.
"""

from dataclasses import dataclass, field

from bot.core import emojis

# --- combat constants ---
START_ENERGY = 3
ENERGY_REGEN = 1
BLEED_DAMAGE = 5
POISON_DAMAGE = 5
WEAKEN_AMOUNT = 6
EMPOWER_AMOUNT = 6
EXECUTE_THRESHOLD = 30  # Finisher gets its bonus against a target at or below this HP
EXECUTE_BONUS = 30

# --- progression / stat constants ---
BASE_HP = 100
BASE_ENERGY = 6
HP_PER_LEVEL = 8
XP_PER_LEVEL = 100
START_RATING = 1000
RANK_MAX_GAP = 400  # ranked is blocked if ratings differ by more than this
LOADOUT_SIZE = 4  # chosen abilities, on top of the universal Strike


@dataclass
class Ability:
    name: str
    cost: int
    price: int = 0  # 0 = a starter ability (unlocked for everyone)
    damage: int = 0
    shield: int = 0
    heal: int = 0
    energy: int = 0  # energy granted to the user
    bleed: int = 0  # bleed turns applied to the target
    poison: int = 0  # poison turns applied to the target
    weaken: int = 0  # weaken turns applied to the target
    empower: int = 0  # empower turns applied to the user
    stun: bool = False  # target skips their next turn
    lifesteal: bool = False  # heal half of damage dealt
    execute: bool = False  # bonus damage to a low-HP target
    desc: str = ""


# Strike is universal (everyone always has it). The rest are slotted into a
# loadout; starter abilities (price 0) come unlocked, the others are bought.
#
# Balance intent: Strike is weak chip you fall back on when out of energy. Heavy
# Blow is the efficient workhorse (great damage per energy). Finisher is the
# executioner: weaker than Heavy on a healthy target, but the strongest hit in
# the game against a wounded one. Guard fully soaks a Heavy, and Focus banks the
# energy needed to chain Heavies or set up a Finisher.
ABILITIES = {
    "strike": Ability("Strike", cost=0, damage=8, desc="Weak free jab. Your fallback when out of energy."),
    "focus": Ability("Focus", cost=0, energy=3, desc="Skip your hit to bank energy for a big turn."),
    "guard": Ability("Guard", cost=1, shield=22, desc="A shield that soaks a Heavy Blow."),
    "heavy": Ability("Heavy Blow", cost=3, damage=22, desc="The efficient workhorse hit."),
    "bleed": Ability("Bleeding Cut", cost=2, damage=6, bleed=3, desc="Light hit plus bleed over time."),
    "mend": Ability("Mend", cost=3, price=500, heal=24, desc="Heal yourself."),
    "concuss": Ability("Concussive Blow", cost=4, price=900, damage=10, stun=True, desc="Damage and stun a turn."),
    "venom": Ability("Venom", cost=2, price=500, poison=4, desc="Heavy damage over time, ignores shields."),
    "cripple": Ability("Cripple", cost=2, price=600, damage=5, weaken=3, desc="Lower the target's attack."),
    "sharpen": Ability("Sharpen", cost=1, price=600, empower=3, desc="Raise your own attack."),
    "drain": Ability("Drain", cost=3, price=900, damage=14, lifesteal=True, desc="Hit and heal off the damage."),
    "finisher": Ability(
        "Finisher", cost=5, price=1200, damage=18, execute=True, desc="Devastating against low-HP foes."
    ),
}
STARTER_ABILITIES = [aid for aid, ab in ABILITIES.items() if ab.price == 0 and aid != "strike"]
DEFAULT_LOADOUT = ["focus", "guard", "heavy", "bleed"]

# Gear: id -> slot/name/price plus the stats it grants.
GEAR = {
    "rusty_sword": {"slot": "weapon", "name": "Rusty Sword", "price": 150, "attack": 3},
    "steel_sword": {"slot": "weapon", "name": "Steel Sword", "price": 600, "attack": 7},
    "warblade": {"slot": "weapon", "name": "Warblade", "price": 1500, "attack": 12},
    "leather_armor": {"slot": "armor", "name": "Leather Armor", "price": 150, "defense": 2, "max_hp": 10},
    "chainmail": {"slot": "armor", "name": "Chainmail", "price": 600, "defense": 4, "max_hp": 25},
    "plate_armor": {"slot": "armor", "name": "Plate Armor", "price": 1500, "defense": 7, "max_hp": 45},
    "power_band": {"slot": "accessory", "name": "Power Band", "price": 400, "max_energy": 1},
    "battle_charm": {"slot": "accessory", "name": "Battle Charm", "price": 1200, "max_energy": 2, "attack": 3},
}


@dataclass
class Combatant:
    name: str
    max_hp: int = BASE_HP
    hp: int = BASE_HP
    max_energy: int = BASE_ENERGY
    energy: int = START_ENERGY
    attack: int = 0
    defense: int = 0
    shield: int = 0
    bleed: int = 0
    poison: int = 0
    weaken: int = 0
    empower: int = 0
    stun: bool = False
    loadout: list = field(default_factory=lambda: list(DEFAULT_LOADOUT))


@dataclass
class DuelState:
    fighters: list  # [Combatant, Combatant]
    active: int = 0
    turn: int = 1


# --- stat aggregation & progression ---
def level_for_xp(xp):
    return 1 + xp // XP_PER_LEVEL


def aggregate_stats(level, weapon=None, armor=None, accessory=None):
    """Combine level and equipped gear into combat stats."""
    stats = {"max_hp": BASE_HP + (level - 1) * HP_PER_LEVEL, "max_energy": BASE_ENERGY, "attack": 0, "defense": 0}
    for item_id in (weapon, armor, accessory):
        gear = GEAR.get(item_id)
        if gear:
            for key in ("max_hp", "max_energy", "attack", "defense"):
                stats[key] += gear.get(key, 0)
    return stats


def make_combatant(name, stats, loadout):
    return Combatant(
        name=name,
        max_hp=stats["max_hp"],
        hp=stats["max_hp"],
        max_energy=stats["max_energy"],
        energy=min(START_ENERGY, stats["max_energy"]),
        attack=stats["attack"],
        defense=stats["defense"],
        loadout=[a for a in loadout if a in ABILITIES][:LOADOUT_SIZE],
    )


def new_duel(c1, c2, first=0):
    return DuelState(fighters=[c1, c2], active=first, turn=1)


# --- combat ---
def _effective_attack(c):
    bonus = (EMPOWER_AMOUNT if c.empower > 0 else 0) - (WEAKEN_AMOUNT if c.weaken > 0 else 0)
    return c.attack + bonus


def _deal(target, raw):
    """Apply raw damage: reduced by defense, then soaked by shield."""
    incoming = max(1, raw - target.defense)
    absorbed = min(target.shield, incoming)
    target.shield -= absorbed
    dealt = incoming - absorbed
    target.hp = max(0, target.hp - dealt)
    return dealt, absorbed


def available_moves(state):
    """Affordable ability ids for the active fighter (Strike plus their loadout)."""
    actor = state.fighters[state.active]
    pool = ["strike"] + [a for a in actor.loadout if a != "strike"]
    return [a for a in pool if a in ABILITIES and ABILITIES[a].cost <= actor.energy]


def _handover(state, log):
    """Switch to the other fighter and process their turn start (DoTs, buff decay,
    regen), skipping stunned turns. Returns the winner Combatant or None."""
    while True:
        state.active = 1 - state.active
        state.turn += 1
        f = state.fighters[state.active]
        opp = state.fighters[1 - state.active]
        if f.bleed > 0:
            f.hp = max(0, f.hp - BLEED_DAMAGE)
            f.bleed -= 1
            log.append(f"{emojis.BLEED} {f.name} bleeds for {BLEED_DAMAGE}.")
        if f.poison > 0 and f.hp > 0:
            f.hp = max(0, f.hp - POISON_DAMAGE)
            f.poison -= 1
            log.append(f"{emojis.POISON} {f.name} takes {POISON_DAMAGE} poison damage.")
        if f.hp <= 0:
            return opp
        if f.weaken > 0:
            f.weaken -= 1
        if f.empower > 0:
            f.empower -= 1
        f.energy = min(f.max_energy, f.energy + ENERGY_REGEN)
        if f.stun:
            f.stun = False
            log.append(f"{emojis.STUN} {f.name} is stunned and skips the turn.")
            continue
        return None


def step(state, ability_id):
    """Resolve the active fighter using `ability_id`. Returns (state, log, winner)
    where winner is the winning Combatant or None. Raises ValueError on an illegal
    move (not in the fighter's kit, unknown, or unaffordable)."""
    actor = state.fighters[state.active]
    target = state.fighters[1 - state.active]
    if ability_id not in ABILITIES:
        raise ValueError(f"unknown ability {ability_id!r}")
    if ability_id != "strike" and ability_id not in actor.loadout:
        raise ValueError(f"{actor.name} does not have {ability_id}")
    ab = ABILITIES[ability_id]
    if ab.cost > actor.energy:
        raise ValueError("not enough energy")

    log = []
    actor.energy -= ab.cost
    if ab.energy:
        actor.energy = min(actor.max_energy, actor.energy + ab.energy)
        log.append(f"{emojis.ENERGY} {actor.name} focuses (+{ab.energy} energy).")
    if ab.shield:
        actor.shield += ab.shield
        log.append(f"{emojis.SHIELD} {actor.name} guards (+{ab.shield} shield).")
    if ab.heal:
        actor.hp = min(actor.max_hp, actor.hp + ab.heal)
        log.append(f"💚 {actor.name} mends (+{ab.heal} HP).")
    if ab.empower:
        actor.empower = max(actor.empower, ab.empower)
        log.append(f"🔺 {actor.name} sharpens their attack.")
    if ab.damage:
        raw = ab.damage + _effective_attack(actor)
        if ab.execute and target.hp <= EXECUTE_THRESHOLD:
            raw += EXECUTE_BONUS
        dealt, absorbed = _deal(target, raw)
        if ab.lifesteal:
            actor.hp = min(actor.max_hp, actor.hp + dealt // 2)
        note = f" ({absorbed} blocked)" if absorbed else ""
        log.append(f"{emojis.DUEL} {actor.name} uses {ab.name} for {dealt}{note}.")
    if ab.bleed:
        target.bleed = max(target.bleed, ab.bleed)
        log.append(f"{emojis.BLEED} {target.name} is bleeding.")
    if ab.poison:
        target.poison = max(target.poison, ab.poison)
        log.append(f"{emojis.POISON} {target.name} is poisoned.")
    if ab.weaken:
        target.weaken = max(target.weaken, ab.weaken)
        log.append(f"🔻 {target.name}'s attack is lowered.")
    if ab.stun:
        target.stun = True
        log.append(f"{emojis.STUN} {target.name} will be stunned.")

    if target.hp <= 0:
        return state, log, actor
    winner = _handover(state, log)
    return state, log, winner


# --- deterministic AI (for the PvE arena) ---
def ai_choose(state):
    """A simple, deterministic policy for the arena bot."""
    moves = available_moves(state)
    me = state.fighters[state.active]
    opp = state.fighters[1 - state.active]
    if "mend" in moves and me.hp < me.max_hp * 0.4:
        return "mend"
    if "finisher" in moves and opp.hp <= EXECUTE_THRESHOLD:
        return "finisher"
    if "concuss" in moves and not opp.stun:
        return "concuss"
    if "drain" in moves and me.hp < me.max_hp * 0.7:
        return "drain"
    if "heavy" in moves:
        return "heavy"
    if "venom" in moves and opp.poison == 0:
        return "venom"
    if "bleed" in moves and opp.bleed == 0:
        return "bleed"
    if me.energy < 2 and "focus" in moves:
        return "focus"
    return "strike"


# --- ELO ---
def elo_expected(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def elo_update(winner_rating, loser_rating, k=32):
    """Return (new_winner_rating, new_loser_rating) after a decisive result."""
    expected_w = elo_expected(winner_rating, loser_rating)
    new_w = round(winner_rating + k * (1 - expected_w))
    new_l = round(loser_rating - k * (1 - expected_w))
    return new_w, new_l


def can_rank(rating_a, rating_b, max_gap=RANK_MAX_GAP):
    return abs(rating_a - rating_b) <= max_gap
