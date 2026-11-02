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
EMPOWER_AMOUNT = 8
EXECUTE_THRESHOLD = 30  # Finisher gets its bonus against a target at or below this percent of max HP
EXECUTE_BONUS = 30
MAX_TURNS = 40  # anti-stall: past this many half-turns the duel is called on HP ratio
MOMENTUM_MAX = 5  # stack cap
MOMENTUM_ATTACK = 2  # attack per momentum stack, so aggression ramps
MOMENTUM_RESETTERS = ("guard", "mend")  # turtling drops your momentum
RIPOSTE_DAMAGE = 12  # dealt to an attacker whose hit gets absorbed by a riposte shield
RUPTURE_PER_TURN = 8  # damage per bleed/poison turn consumed by Rupture
EXPOSE_AMOUNT = 5  # extra damage from every hit taken while exposed
VENGEANCE_DIVISOR = 4  # Vengeance gains 1 damage per this many percent of your HP missing
SECOND_MOVER_ENERGY = 2  # player duels only: going first otherwise wins about 60-65% of even matches
LAST_STAND_PERCENT = 10  # Phoenix Charm leaves you on this percent of max HP

# Sentinel returned by step() as the "winner" when a duel is called as a tie at the
# turn cap. The cog treats it as a refunded, no-XP draw.
DRAW = object()

# --- progression / stat constants ---
BASE_HP = 100
BASE_ENERGY = 6
HP_PER_LEVEL = 8
HP_LEVEL_CAP = 20  # levels past this add no HP, and ranked gives everyone this level's HP
WAGER_RAKE_PERCENT = 5  # the house's cut of a wagered duel's pot
XP_PER_LEVEL = 100
START_RATING = 1000
RANK_MAX_GAP = 400  # ranked is blocked if ratings differ by more than this
LOADOUT_SIZE = 4  # chosen abilities, on top of the universal Strike
RATING_FLOOR = 800  # ranked rating never drops below this
RANKED_K_NEW = 40  # K-factor while placing (first RANKED_K_GAMES ranked games)
RANKED_K = 24  # K-factor after placement
RANKED_K_GAMES = 10
ENHANCE_MAX = 5  # gear enhancement cap (+5)
ENHANCE_BASE = 150  # enhancing to +n costs ENHANCE_BASE * 2**n (300/600/1200/2400/4800)
ENHANCE_HP_PER = 4  # accessory enhancement grants this much max HP per level

# Arena tower tuning.
ARENA_DAILY_CAP = 5  # attempts per UTC day, so the tower is an appointment, not a binge
ARENA_CLEAR_BASE = 20  # first-clear coins = base + per_floor * floor (+ boss bonus)
ARENA_CLEAR_PER_FLOOR = 10
ARENA_BOSS_BONUS = 100  # every 5th floor is a boss
ARENA_ATTACK_PER_FLOOR = 1
ARENA_HP_PER_FLOOR = 0.05  # +5% HP per floor


@dataclass
class Ability:
    name: str
    cost: int
    price: int = 0  # 0 = a starter ability (unlocked for everyone)
    damage: int = 0
    shield: int = 0
    heal: int = 0
    heal_pct: int = 0  # more healing, as a percent of max HP, so it keeps up with gear and levels
    energy: int = 0  # energy granted to the user
    bleed: int = 0  # bleed turns applied to the target
    poison: int = 0  # poison turns applied to the target
    weaken: int = 0  # weaken turns applied to the target
    empower: int = 0  # empower turns applied to the user
    stun: bool = False  # target skips their next turn
    lifesteal: bool = False  # heal half of damage dealt
    execute: bool = False  # bonus damage to a low-HP target
    cooldown: int = 0  # turns before it can be used again (0 = none)
    hits: int = 1  # damage applies this many times, each hit weaker: full, half, a third
    shatter: bool = False  # destroy ALL target shield before dealing damage
    cleanse: bool = False  # clear the user's own bleed, poison, and weaken
    rupture: bool = False  # consume the target's bleed/poison turns for burst damage
    desperate: bool = False  # only usable below half HP
    riposte: bool = False  # if the granted shield absorbs a hit, the attacker takes damage
    pierce: bool = False  # ignores the target's defense and shield
    recoil: int = 0  # damage the user takes for using it (never below 1 HP)
    evade: bool = False  # the next hit against the user before their next turn misses
    unleash: int = 0  # bonus damage per momentum stack, spending all of them
    sap: int = 0  # energy the target loses
    expose: int = 0  # turns the target takes EXPOSE_AMOUNT more from every hit
    vengeance: bool = False  # hits harder the more HP the user has lost
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
    "guard": Ability("Guard", cost=1, cooldown=2, shield=22, desc="A shield that soaks a Heavy Blow."),
    "heavy": Ability("Heavy Blow", cost=3, damage=22, desc="The efficient workhorse hit."),
    "bleed": Ability("Bleeding Cut", cost=2, damage=6, bleed=3, desc="Light hit plus bleed over time."),
    "mend": Ability(
        "Mend", cost=3, price=500, cooldown=3, heal=16, heal_pct=15, desc="Heal 16, plus 15% of your max HP."
    ),
    "concuss": Ability(
        "Concussive Blow", cost=4, price=900, cooldown=5, damage=10, stun=True, desc="Damage and stun a turn."
    ),
    "venom": Ability(
        "Venom", cost=2, price=500, damage=2, poison=4, desc="A light hit plus heavy poison, which ignores shields."
    ),
    "cripple": Ability("Cripple", cost=2, price=600, damage=5, weaken=3, desc="Lower the target's attack."),
    "sharpen": Ability("Sharpen", cost=1, price=600, cooldown=3, empower=3, desc="+8 attack on your next 2 turns."),
    "drain": Ability(
        "Drain", cost=3, price=900, cooldown=2, damage=12, lifesteal=True, desc="Hit and heal half the damage."
    ),
    "finisher": Ability(
        "Finisher",
        cost=4,
        price=1200,
        cooldown=2,
        damage=18,
        execute=True,
        desc="30 extra damage to a target under 30% HP.",
    ),
    # Synergy archetypes (Phase C): each is a decision point in a counter-web, not a stat stick.
    "rupture": Ability(
        "Rupture",
        cost=2,
        price=800,
        rupture=True,
        desc="Burst the target's bleed and poison: 8 damage per turn consumed.",
    ),
    "shatter": Ability(
        "Shatter", cost=3, price=900, damage=12, shatter=True, desc="Destroy ALL of the target's shield, then hit."
    ),
    "ward": Ability(
        "Ward",
        cost=2,
        price=800,
        shield=14,
        cleanse=True,
        desc="Clear your own bleed, poison, weaken and exposure, plus a small shield.",
    ),
    "twinstrike": Ability(
        "Twinstrike",
        cost=2,
        price=700,
        damage=9,
        hits=2,
        desc="Two quick hits: 9, then half that. Their defense counts against each.",
    ),
    "adrenaline": Ability(
        "Adrenaline",
        cost=1,
        price=700,
        energy=2,
        heal=8,
        desperate=True,
        desc="Below half HP only: surge 2 energy and patch 8 HP.",
    ),
    "riposte": Ability(
        "Riposte",
        cost=2,
        price=900,
        shield=12,
        riposte=True,
        desc="Shield up. If it blocks anything before your next turn, the attacker takes 12.",
    ),
    # A second counter-web: each one answers something the older abilities had no reply to.
    "pierce": Ability(
        "Piercing Thrust",
        cost=3,
        price=1500,
        cooldown=2,
        damage=14,
        pierce=True,
        desc="14 damage that goes straight through defense and shields.",
    ),
    "reckless": Ability(
        "Reckless Swing", cost=2, price=1000, damage=20, recoil=6, desc="A big cheap hit, but you take 6 yourself."
    ),
    "sidestep": Ability(
        "Sidestep",
        cost=1,
        price=1200,
        cooldown=3,
        evade=True,
        desc="The next hit misses, its effects too, and costs them their momentum. A second hit and wounds still land.",
    ),
    "unleash": Ability(
        "Unleash",
        cost=2,
        price=1500,
        damage=6,
        unleash=4,
        desc="Spend all your momentum for 4 extra damage per stack.",
    ),
    "siphon": Ability(
        "Siphon", cost=1, price=1000, cooldown=3, damage=4, sap=2, desc="A light hit that drains 2 of their energy."
    ),
    "expose": Ability(
        "Expose",
        cost=2,
        price=1200,
        damage=4,
        expose=4,
        desc="A light hit. For their next 3 turns, every hit on them deals 5 more.",
    ),
    "vengeance": Ability(
        "Vengeance",
        cost=3,
        price=1500,
        damage=6,
        vengeance=True,
        desc="6 damage, plus 1 for every 4% of your HP that's gone.",
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
    # Top-tier sidegrades (Phase C): horizontal choices, not strictly better.
    "duelist_rapier": {"slot": "weapon", "name": "Duelist Rapier", "price": 1500, "attack": 11, "max_energy": 2},
    "berserker_axe": {"slot": "weapon", "name": "Berserker Axe", "price": 1500, "attack": 14, "max_hp": -20},
    "spellwoven_cloak": {
        "slot": "armor",
        "name": "Spellwoven Cloak",
        "price": 1500,
        "defense": 6,
        "max_hp": 60,
        "max_energy": 1,
    },
    "momentum_locket": {
        "slot": "accessory",
        "name": "Momentum Locket",
        "price": 1200,
        "attack": 3,
        "keep_momentum": True,
        "desc": "Keep 1 momentum stack when it resets",
    },
    "regen_ring": {
        "slot": "accessory",
        "name": "Regen Ring",
        "price": 1200,
        "regen": 3,
        "desc": "+3 HP at the start of each of your turns",
    },
    # Passive gear: each one opens a build rather than adding bigger numbers.
    "vampiric_blade": {
        "slot": "weapon",
        "name": "Vampiric Blade",
        "price": 3000,
        "attack": 8,
        "leech": 25,
        "desc": "Heal a quarter of the damage your hits deal",
    },
    "serrated_edge": {
        "slot": "weapon",
        "name": "Serrated Edge",
        "price": 3000,
        "attack": 11,
        "dot_bonus": 1,
        "desc": "Your bleed and poison last a turn longer",
    },
    "sundering_maul": {
        "slot": "weapon",
        "name": "Sundering Maul",
        "price": 3000,
        "attack": 9,
        "armor_pen": 3,
        "desc": "Your hits ignore 3 of their defense",
    },
    "thornmail": {
        "slot": "armor",
        "name": "Thornmail",
        "price": 3000,
        "defense": 5,
        "max_hp": 25,
        "thorns": 4,
        "desc": "Anyone who hits you takes 4 per hit",
    },
    "juggernaut_plate": {
        "slot": "armor",
        "name": "Juggernaut Plate",
        "price": 3000,
        "defense": 9,
        "max_hp": 25,
        "max_energy": -1,
    },
    "phoenix_charm": {
        "slot": "accessory",
        "name": "Phoenix Charm",
        "price": 3000,
        "last_stand": True,
        "desc": "Once per duel, a killing hit leaves you on 10% HP instead",
    },
    "war_drum": {
        "slot": "accessory",
        "name": "War Drum",
        "price": 3000,
        "start_momentum": 3,
        "desc": "Start every duel with 3 momentum",
    },
    "aegis_pendant": {
        "slot": "accessory",
        "name": "Aegis Pendant",
        "price": 3000,
        "start_shield": 30,
        "desc": "Start every duel behind a 30 point shield",
    },
}

# Gear passives that add up across slots and carry onto the Combatant by name.
PASSIVES = ("regen", "leech", "dot_bonus", "armor_pen", "thorns", "start_momentum", "start_shield")


def enhance_cost(current_level):
    """Coins to enhance a piece of gear from its current level to the next."""
    return ENHANCE_BASE * 2 ** (current_level + 1)


def enhance_bonus(slot, level):
    """Stat bonus a gear piece gains from its enhancement level."""
    if slot == "weapon":
        return {"attack": level}
    if slot == "armor":
        return {"defense": level}
    return {"max_hp": ENHANCE_HP_PER * level}


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
    momentum: int = 0  # 🔥 stacks: +MOMENTUM_ATTACK attack each, reset by turtling
    riposte_ready: bool = False  # a riposte shield is up until this fighter's next turn
    exposed: int = 0  # turns of taking EXPOSE_AMOUNT more from every hit
    evading: bool = False  # the next hit misses, until this fighter's next turn
    regen: int = 0  # HP regained at each of this fighter's turn starts (gear passive)
    keep_momentum: bool = False  # keep 1 stack on momentum reset (gear passive)
    leech: int = 0  # percent of hit damage healed (gear passive)
    dot_bonus: int = 0  # extra turns on the bleed and poison this fighter applies (gear passive)
    armor_pen: int = 0  # defense this fighter's hits ignore (gear passive)
    thorns: int = 0  # damage an attacker takes per hit on this fighter (gear passive)
    last_stand: bool = False  # survive one killing hit on 1 HP (gear passive)
    cooldowns: dict = field(default_factory=dict)  # ability id -> turns until usable again
    loadout: list = field(default_factory=lambda: list(DEFAULT_LOADOUT))


@dataclass
class DuelState:
    fighters: list  # [Combatant, Combatant]
    active: int = 0
    turn: int = 1


# --- stat aggregation & progression ---
def level_for_xp(xp):
    return 1 + xp // XP_PER_LEVEL


def wager_prize(bet):
    """What the winner of a wagered duel takes: both antes less the house's cut.
    The cut rounds down, so a pot under 20 coins pays out whole."""
    pot = bet * 2
    return pot - pot * WAGER_RAKE_PERCENT // 100


def aggregate_stats(level, weapon=None, armor=None, accessory=None, gear_levels=None):
    """Combine level, equipped gear, and gear enhancement levels into combat stats.
    ``gear_levels`` maps item id -> enhancement level (missing items count as +0)."""
    stats = {
        "max_hp": BASE_HP + (min(level, HP_LEVEL_CAP) - 1) * HP_PER_LEVEL,
        "max_energy": BASE_ENERGY,
        "attack": 0,
        "defense": 0,
        "keep_momentum": False,
        "last_stand": False,
        **dict.fromkeys(PASSIVES, 0),
    }
    for item_id in (weapon, armor, accessory):
        gear = GEAR.get(item_id)
        if not gear:
            continue
        for key in ("max_hp", "max_energy", "attack", "defense", *PASSIVES):
            stats[key] += gear.get(key, 0)
        stats["keep_momentum"] = stats["keep_momentum"] or gear.get("keep_momentum", False)
        stats["last_stand"] = stats["last_stand"] or gear.get("last_stand", False)
        for key, bonus in enhance_bonus(gear["slot"], (gear_levels or {}).get(item_id, 0)).items():
            stats[key] += bonus
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
        shield=stats.get("start_shield", 0),
        momentum=stats.get("start_momentum", 0),
        regen=stats.get("regen", 0),
        keep_momentum=stats.get("keep_momentum", False),
        leech=stats.get("leech", 0),
        dot_bonus=stats.get("dot_bonus", 0),
        armor_pen=stats.get("armor_pen", 0),
        thorns=stats.get("thorns", 0),
        last_stand=stats.get("last_stand", False),
        loadout=[a for a in loadout if a in ABILITIES][:LOADOUT_SIZE],
    )


def new_duel(c1, c2, first=0, second_energy=0):
    second = (c1, c2)[1 - first]
    second.energy = min(second.max_energy, second.energy + second_energy)
    return DuelState(fighters=[c1, c2], active=first, turn=1)


# --- combat ---
def _effective_attack(c):
    bonus = (EMPOWER_AMOUNT if c.empower > 0 else 0) - (WEAKEN_AMOUNT if c.weaken > 0 else 0)
    return c.attack + bonus + MOMENTUM_ATTACK * c.momentum


def _in_execute_range(c):
    return c.hp * 100 <= c.max_hp * EXECUTE_THRESHOLD


def _reset_momentum(c):
    c.momentum = min(c.momentum, 1) if c.keep_momentum else 0


def _deal(target, raw, armor_pen=0, pierce=False):
    """Apply raw damage: reduced by defense, then soaked by shield. Exposure adds to
    every hit, and a piercing one skips both defense and shield."""
    if target.exposed:
        raw += EXPOSE_AMOUNT
    if pierce:
        dealt = max(1, raw)
        target.hp = max(0, target.hp - dealt)
        return dealt, 0
    incoming = max(1, raw - max(0, target.defense - armor_pen))
    absorbed = min(target.shield, incoming)
    target.shield -= absorbed
    dealt = incoming - absorbed
    target.hp = max(0, target.hp - dealt)
    return dealt, absorbed


def available_moves(state):
    """Legal ability ids for the active fighter: in their kit, affordable, off
    cooldown, and (for desperate moves) below half HP."""
    actor = state.fighters[state.active]
    pool = ["strike"] + [a for a in actor.loadout if a != "strike"]
    out = []
    for aid in pool:
        ab = ABILITIES.get(aid)
        if ab is None or ab.cost > actor.energy:
            continue
        if actor.cooldowns.get(aid, 0) > 0:
            continue
        if ab.desperate and actor.hp * 2 >= actor.max_hp:
            continue
        out.append(aid)
    return out


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
        if f.regen and f.hp < f.max_hp:
            f.hp = min(f.max_hp, f.hp + f.regen)
            log.append(f"{emojis.HEALTH} {f.name} regenerates {f.regen} HP.")
        if f.weaken > 0:
            f.weaken -= 1
        if f.empower > 0:
            f.empower -= 1
        if f.exposed > 0:
            f.exposed -= 1
        for aid in f.cooldowns:
            if f.cooldowns[aid] > 0:
                f.cooldowns[aid] -= 1
        f.riposte_ready = False  # the riposte window closes at your next turn
        f.evading = False  # and so does a sidestep
        f.energy = min(f.max_energy, f.energy + ENERGY_REGEN)
        if f.stun:
            f.stun = False
            log.append(f"{emojis.STUN} {f.name} is stunned and skips the turn.")
            continue
        return None


def _cap_result(state):
    """Decide a duel that reached the turn cap by remaining HP ratio. Returns the
    Combatant with the higher ratio, or DRAW when they are level."""
    f0, f1 = state.fighters
    r0, r1 = f0.hp / f0.max_hp, f1.hp / f1.max_hp
    if r0 > r1:
        return f0
    if r1 > r0:
        return f1
    return DRAW


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
    if actor.cooldowns.get(ability_id, 0) > 0:
        raise ValueError(f"{ab.name} is on cooldown")
    if ab.desperate and actor.hp * 2 >= actor.max_hp:
        raise ValueError(f"{ab.name} needs you below half HP")

    log = []
    actor.energy -= ab.cost
    if ab.cooldown:
        actor.cooldowns[ability_id] = ab.cooldown
    dealt_total = 0
    landed = not ab.damage  # a move with no hit can't be dodged
    if ab.cleanse and (actor.bleed or actor.poison or actor.weaken or actor.exposed):
        actor.bleed = actor.poison = actor.weaken = actor.exposed = 0
        log.append(f"{emojis.SHIELD} {actor.name} wards off their afflictions.")
    if ab.energy:
        actor.energy = min(actor.max_energy, actor.energy + ab.energy)
        log.append(f"{emojis.ENERGY} {actor.name} gains +{ab.energy} energy.")
    if ab.shield:
        actor.shield += ab.shield
        log.append(f"{emojis.SHIELD} {actor.name} guards (+{ab.shield} shield).")
    if ab.riposte:
        actor.riposte_ready = True
        log.append(f"↩️ {actor.name} readies a riposte.")
    if ab.evade:
        actor.evading = True
        log.append(f"💨 {actor.name} gets ready to sidestep.")
    if ab.heal:
        healed = ab.heal + actor.max_hp * ab.heal_pct // 100
        actor.hp = min(actor.max_hp, actor.hp + healed)
        log.append(f"{emojis.HEALTH} {actor.name} mends (+{healed} HP).")
    if ab.empower:
        actor.empower = max(actor.empower, ab.empower)
        log.append(f"🔺 {actor.name} sharpens their attack.")
    if ab.shatter and target.shield:
        log.append(f"{emojis.SHIELD} {actor.name} shatters {target.name}'s shield ({target.shield} destroyed).")
        target.shield = 0
    if ab.damage:
        for _hit in range(ab.hits):
            if target.evading:
                target.evading = False
                _reset_momentum(actor)
                log.append(f"💨 {target.name} sidesteps {ab.name}!")
                continue
            landed = True
            raw = (ab.damage + _effective_attack(actor)) // (_hit + 1)
            if ab.execute and _in_execute_range(target):
                raw += EXECUTE_BONUS
            raw += ab.unleash * actor.momentum
            if ab.vengeance:
                raw += (actor.max_hp - actor.hp) * 100 // actor.max_hp // VENGEANCE_DIVISOR
            dealt, absorbed = _deal(target, raw, actor.armor_pen, ab.pierce)
            dealt_total += dealt
            if ab.lifesteal:
                actor.hp = min(actor.max_hp, actor.hp + dealt // 2)
            if actor.leech:
                actor.hp = min(actor.max_hp, actor.hp + dealt * actor.leech // 100)
            note = f" ({absorbed} blocked)" if absorbed else ""
            log.append(f"{emojis.DUEL} {actor.name} uses {ab.name} for {dealt}{note}.")
            if absorbed and target.riposte_ready:
                target.riposte_ready = False
                actor.hp = max(0, actor.hp - RIPOSTE_DAMAGE)
                log.append(f"↩️ {target.name} ripostes for {RIPOSTE_DAMAGE}!")
            if target.thorns:
                actor.hp = max(0, actor.hp - target.thorns)
                log.append(f"🌵 {actor.name} takes {target.thorns} from the thorns.")
            if target.hp <= 0 or actor.hp <= 0:
                break  # no second hit on a corpse, and no healing back from a killing riposte
    if ab.recoil and actor.hp > 0:
        actor.hp = max(1, actor.hp - ab.recoil)
        log.append(f"💢 {actor.name} takes {ab.recoil} recoil.")
    if ab.sap and landed:
        target.energy = max(0, target.energy - ab.sap)
        log.append(f"{emojis.ENERGY} {target.name} loses {ab.sap} energy.")
    if ab.rupture:
        turns = target.bleed + target.poison
        if turns:
            burst = RUPTURE_PER_TURN * turns
            target.bleed = target.poison = 0
            target.hp = max(0, target.hp - burst)  # like the DoTs it consumes, ignores shield
            dealt_total += burst
            log.append(f"{emojis.BLEED} {actor.name} ruptures the wounds for {burst}.")
        else:
            log.append(f"{actor.name}'s rupture finds no wounds to burst.")
    if ab.bleed and landed:
        target.bleed = max(target.bleed, ab.bleed + actor.dot_bonus)
        log.append(f"{emojis.BLEED} {target.name} is bleeding.")
    if ab.poison and landed:
        target.poison = max(target.poison, ab.poison + actor.dot_bonus)
        log.append(f"{emojis.POISON} {target.name} is poisoned.")
    if ab.weaken and landed:
        target.weaken = max(target.weaken, ab.weaken)
        log.append(f"🔻 {target.name}'s attack is lowered.")
    if ab.expose and landed:
        target.exposed = max(target.exposed, ab.expose)
        log.append(f"🎯 {target.name} is exposed.")
    if ab.stun and landed:
        target.stun = True
        log.append(f"{emojis.STUN} {target.name} will be stunned.")

    # Momentum: landing damage ramps it, turtling or Unleash spends it (locket keeps 1 stack).
    if dealt_total >= 1:
        actor.momentum = min(MOMENTUM_MAX, actor.momentum + 1)
    if ability_id in MOMENTUM_RESETTERS or ab.unleash:
        _reset_momentum(actor)

    for fighter in (target, actor):  # a riposte or thorns can be the killing hit too
        if fighter.hp <= 0 and fighter.last_stand:
            fighter.last_stand = False
            fighter.hp = fighter.max_hp * LAST_STAND_PERCENT // 100
            log.append(f"🪶 {fighter.name} refuses to fall!")
    if target.hp <= 0:
        return state, log, actor
    if actor.hp <= 0:  # a riposte can fell the attacker
        return state, log, target
    winner = _handover(state, log)
    if winner is None and state.turn > MAX_TURNS:
        winner = _cap_result(state)
        if winner is DRAW:
            log.append(f"{emojis.STUN} Turn limit reached. The duel is a draw.")
        else:
            log.append(f"{emojis.STUN} Turn limit reached. {winner.name} wins on remaining HP.")
    return state, log, winner


# --- deterministic AI (for the PvE arena) ---
def ai_choose(state):
    """A simple, deterministic policy for the arena bot."""
    moves = available_moves(state)
    me = state.fighters[state.active]
    opp = state.fighters[1 - state.active]
    if "adrenaline" in moves:  # only legal below half HP
        return "adrenaline"
    if "mend" in moves and me.hp < me.max_hp * 0.4:
        return "mend"
    if "ward" in moves and me.bleed + me.poison >= 2:
        return "ward"
    if "finisher" in moves and _in_execute_range(opp):
        return "finisher"
    if "shatter" in moves and opp.shield >= 12:
        return "shatter"
    if "rupture" in moves and opp.bleed + opp.poison >= 2:
        return "rupture"
    if "concuss" in moves and not opp.stun:
        return "concuss"
    if "drain" in moves and me.hp < me.max_hp * 0.7:
        return "drain"
    if "sharpen" in moves and me.empower == 0:
        return "sharpen"
    if "heavy" in moves:
        return "heavy"
    if "venom" in moves and opp.poison == 0:
        return "venom"
    if "bleed" in moves and opp.bleed == 0:
        return "bleed"
    if "cripple" in moves and opp.weaken == 0:
        return "cripple"
    if "twinstrike" in moves:
        return "twinstrike"
    if "guard" in moves and me.shield == 0 and me.hp < me.max_hp * 0.6:
        return "guard"
    if me.energy < 2 and "focus" in moves:
        return "focus"
    return "strike"


# --- arena tower ---
# Kit archetypes rotate floor by floor so successive floors ask different questions.
ARENA_ARCHETYPES = [
    ("Bruiser", ["heavy", "sharpen", "twinstrike", "focus"]),
    ("Stalker", ["bleed", "venom", "rupture", "focus"]),
    ("Warden", ["concuss", "cripple", "guard", "focus"]),
    ("Bulwark", ["guard", "mend", "ward", "focus"]),
]
ARENA_BOSS_NAMES = ["Ironjaw", "Venomspine", "Gravewarden", "Colossus", "The Ascendant"]


def arena_opponent(floor, player_level):
    """The tower fight for ``floor``: (name, stats, loadout, is_boss). Scales off
    the player's level with +1 attack and +5% HP per floor. Every 5th floor is a
    named boss; its kit stays fixed per floor because the rotation is by floor."""
    name, kit = ARENA_ARCHETYPES[(floor - 1) % len(ARENA_ARCHETYPES)]
    is_boss = floor % 5 == 0
    if is_boss:
        name = ARENA_BOSS_NAMES[(floor // 5 - 1) % len(ARENA_BOSS_NAMES)]
    stats = aggregate_stats(player_level)
    stats["attack"] += floor * ARENA_ATTACK_PER_FLOOR
    stats["max_hp"] = round(stats["max_hp"] * (1 + ARENA_HP_PER_FLOOR * floor))
    return name, stats, kit, is_boss


def arena_reward(floor, is_boss):
    """First-clear coins for a floor (bosses pay a bonus)."""
    return ARENA_CLEAR_BASE + ARENA_CLEAR_PER_FLOOR * floor + (ARENA_BOSS_BONUS if is_boss else 0)


# --- ELO ---
def elo_expected(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def elo_update(winner_rating, loser_rating, k=32, k_loser=None):
    """Return (new_winner_rating, new_loser_rating) after a decisive result.
    Each player can move on their own K (placement games swing harder), and no
    rating ever drops below RATING_FLOOR."""
    expected_w = elo_expected(winner_rating, loser_rating)
    new_w = round(winner_rating + k * (1 - expected_w))
    new_l = round(loser_rating - (k if k_loser is None else k_loser) * (1 - expected_w))
    return max(RATING_FLOOR, new_w), max(RATING_FLOOR, new_l)


def ranked_k(games_played):
    """K-factor for a player: placement games move ratings faster."""
    return RANKED_K_NEW if games_played < RANKED_K_GAMES else RANKED_K


def can_rank(rating_a, rating_b, max_gap=RANK_MAX_GAP):
    return abs(rating_a - rating_b) <= max_gap
