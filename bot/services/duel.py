"""Duel persistence: a duelist per user (level/xp, rating, record, trophies,
equipped gear, ability loadout) plus owned gear and unlocked abilities.

Coin spending lives in the economy service; this only grants/equips what the cog
has already paid for, and tracks combat progression.
"""

import datetime
import sqlite3

from bot.games.duel import (
    ABILITIES,
    DEFAULT_LOADOUT,
    GEAR,
    LOADOUT_SIZE,
    START_RATING,
    STARTER_ABILITIES,
    level_for_xp,
)

# Explicit column order for duelist reads, so rows stay stable no matter what
# order the ALTER TABLE upgrades ran in.
_COLUMNS = (
    "user_id, username, xp, rating, wins, losses, trophies, weapon, armor, accessory, loadout, "
    "arena_floor, arena_day, arena_attempts, ranked_games, ranked_streak"
)


class DuelService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")  # concurrent readers with one writer, safer on crash
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS duelists (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                rating INTEGER NOT NULL DEFAULT 1000,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                trophies INTEGER NOT NULL DEFAULT 0,
                weapon TEXT,
                armor TEXT,
                accessory TEXT,
                loadout TEXT
            )"""
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS duel_gear (user_id INTEGER, item_id TEXT, PRIMARY KEY (user_id, item_id))"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS duel_abilities (user_id INTEGER, ability_id TEXT, PRIMARY KEY (user_id, ability_id))"
        )
        # Upgrade older tables that predate later columns (same pattern as economy).
        cols = [r[1] for r in self._conn.execute("PRAGMA table_info(duelists)")]
        for name, ddl in (
            ("arena_floor", "INTEGER NOT NULL DEFAULT 0"),
            ("arena_day", "TEXT"),
            ("arena_attempts", "INTEGER NOT NULL DEFAULT 0"),
            ("ranked_games", "INTEGER NOT NULL DEFAULT 0"),
            ("ranked_streak", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if name not in cols:
                self._conn.execute(f"ALTER TABLE duelists ADD COLUMN {name} {ddl}")
        gear_cols = [r[1] for r in self._conn.execute("PRAGMA table_info(duel_gear)")]
        if "level" not in gear_cols:
            self._conn.execute("ALTER TABLE duel_gear ADD COLUMN level INTEGER NOT NULL DEFAULT 0")
        self._conn.commit()

    def _row_to_dict(self, row):
        d = {
            "user_id": row[0],
            "username": row[1],
            "xp": row[2],
            "rating": row[3],
            "wins": row[4],
            "losses": row[5],
            "trophies": row[6],
            "weapon": row[7],
            "armor": row[8],
            "accessory": row[9],
            "loadout": [a for a in (row[10] or "").split(",") if a],
            "arena_floor": row[11],
            "arena_day": row[12],
            "arena_attempts": row[13],
            "ranked_games": row[14],
            "ranked_streak": row[15],
        }
        d["level"] = level_for_xp(d["xp"])
        return d

    def get(self, user_id):
        row = self._conn.execute(f"SELECT {_COLUMNS} FROM duelists WHERE user_id = ?", (user_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_or_create(self, user_id, username):
        existing = self.get(user_id)
        if existing:
            return existing
        self._conn.execute(
            "INSERT INTO duelists (user_id, username, rating, loadout) VALUES (?, ?, ?, ?)",
            (user_id, username, START_RATING, ",".join(DEFAULT_LOADOUT)),
        )
        self._conn.executemany(
            "INSERT OR IGNORE INTO duel_abilities (user_id, ability_id) VALUES (?, ?)",
            [(user_id, aid) for aid in STARTER_ABILITIES],
        )
        self._conn.commit()
        return self.get(user_id)

    def add_xp(self, user_id, username, amount):
        """Add account XP outside a match (a game win or quest reward). Returns
        ``(new_level, leveled_up)``."""
        rec = self.get_or_create(user_id, username)
        self._conn.execute(
            "UPDATE duelists SET username = ?, xp = xp + ? WHERE user_id = ?", (username, amount, user_id)
        )
        self._conn.commit()
        new_level = level_for_xp(rec["xp"] + amount)
        return new_level, new_level > rec["level"]

    # --- gear ---
    def owns_gear(self, user_id, item_id):
        return (
            self._conn.execute(
                "SELECT 1 FROM duel_gear WHERE user_id = ? AND item_id = ?", (user_id, item_id)
            ).fetchone()
            is not None
        )

    def owned_gear(self, user_id):
        return [r[0] for r in self._conn.execute("SELECT item_id FROM duel_gear WHERE user_id = ?", (user_id,))]

    def grant_gear(self, user_id, item_id):
        self._conn.execute("INSERT OR IGNORE INTO duel_gear (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
        self._conn.commit()

    def gear_level(self, user_id, item_id):
        row = self._conn.execute(
            "SELECT level FROM duel_gear WHERE user_id = ? AND item_id = ?", (user_id, item_id)
        ).fetchone()
        return row[0] if row else 0

    def gear_levels(self, user_id):
        """All owned gear as {item_id: enhancement_level}."""
        return dict(self._conn.execute("SELECT item_id, level FROM duel_gear WHERE user_id = ?", (user_id,)))

    def enhance_gear(self, user_id, item_id):
        """Raise an owned item's enhancement by one. Returns the new level.
        Affordability and the +5 cap are the caller's checks."""
        self._conn.execute(
            "UPDATE duel_gear SET level = level + 1 WHERE user_id = ? AND item_id = ?", (user_id, item_id)
        )
        self._conn.commit()
        return self.gear_level(user_id, item_id)

    def max_gear_level(self, user_id):
        """The user's highest enhancement level (for the Honed achievement)."""
        row = self._conn.execute("SELECT MAX(level) FROM duel_gear WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] or 0

    # --- arena tower ---
    def use_arena_attempt(self, user_id, cap, today=None):
        """Spend one of today's arena attempts. Returns ``(allowed, remaining_after)``.
        The counter resets when the stored day is not today (UTC)."""
        today = today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        rec = self.get(user_id)
        used = rec["arena_attempts"] if rec and rec["arena_day"] == today else 0
        if used >= cap:
            return False, 0
        self._conn.execute(
            "UPDATE duelists SET arena_day = ?, arena_attempts = ? WHERE user_id = ?", (today, used + 1, user_id)
        )
        self._conn.commit()
        return True, cap - used - 1

    def advance_arena_floor(self, user_id):
        """Record a floor clear. Returns the new highest cleared floor."""
        self._conn.execute("UPDATE duelists SET arena_floor = arena_floor + 1 WHERE user_id = ?", (user_id,))
        self._conn.commit()
        return self.get(user_id)["arena_floor"]

    def equip(self, user_id, item_id):
        """Equip owned gear into its slot. Returns 'equipped', 'unowned', or 'unknown'."""
        if item_id not in GEAR:
            return "unknown"
        if not self.owns_gear(user_id, item_id):
            return "unowned"
        slot = GEAR[item_id]["slot"]  # weapon | armor | accessory
        self._conn.execute(f"UPDATE duelists SET {slot} = ? WHERE user_id = ?", (item_id, user_id))
        self._conn.commit()
        return "equipped"

    # --- abilities ---
    def has_ability(self, user_id, ability_id):
        return (
            self._conn.execute(
                "SELECT 1 FROM duel_abilities WHERE user_id = ? AND ability_id = ?", (user_id, ability_id)
            ).fetchone()
            is not None
        )

    def unlocked_abilities(self, user_id):
        return [r[0] for r in self._conn.execute("SELECT ability_id FROM duel_abilities WHERE user_id = ?", (user_id,))]

    def unlock_ability(self, user_id, ability_id):
        self._conn.execute(
            "INSERT OR IGNORE INTO duel_abilities (user_id, ability_id) VALUES (?, ?)", (user_id, ability_id)
        )
        self._conn.commit()

    def set_loadout(self, user_id, ability_ids):
        """Set the loadout. Returns 'ok', 'too_many', 'unknown', or 'locked'."""
        ids = [a for a in ability_ids if a]
        if len(ids) > LOADOUT_SIZE:
            return "too_many"
        for aid in ids:
            if aid == "strike" or aid not in ABILITIES:
                return "unknown"
            if not self.has_ability(user_id, aid):
                return "locked"
        self._conn.execute("UPDATE duelists SET loadout = ? WHERE user_id = ?", (",".join(ids), user_id))
        self._conn.commit()
        return "ok"

    # --- results ---
    def apply_match(self, user_id, username, won, xp_gain, new_rating=None, trophies=0, ranked=False):
        """Record one player's match outcome (W/L, xp, optional new rating, trophies).
        ``ranked`` also bumps the placement counter and the ranked win streak.
        Returns ``(new_level, leveled_up)`` so the caller can announce a level-up."""
        rec = self.get_or_create(user_id, username)
        sets = ["username = ?", "xp = xp + ?", "wins = wins + ?", "losses = losses + ?", "trophies = trophies + ?"]
        params = [username, xp_gain, 1 if won else 0, 0 if won else 1, trophies]
        if new_rating is not None:
            sets.append("rating = ?")
            params.append(new_rating)
        if ranked:
            sets.append("ranked_games = ranked_games + 1")
            sets.append("ranked_streak = ranked_streak + 1" if won else "ranked_streak = 0")
        params.append(user_id)
        self._conn.execute(f"UPDATE duelists SET {', '.join(sets)} WHERE user_id = ?", params)
        self._conn.commit()
        new_level = level_for_xp(rec["xp"] + xp_gain)
        return new_level, new_level > rec["level"]

    def top(self, limit=10):
        return self._conn.execute(
            "SELECT username, rating, wins, losses, ranked_streak FROM duelists ORDER BY rating DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def reset_season(self):
        """Reset every duelist's rating and trophies to default. Returns the
        pre-reset top duelist as ``(username, rating)`` (the season champion), or None."""
        champ = self._conn.execute("SELECT username, rating FROM duelists ORDER BY rating DESC LIMIT 1").fetchone()
        self._conn.execute("UPDATE duelists SET rating = ?, trophies = 0", (START_RATING,))
        self._conn.commit()
        return champ

    def close(self):
        self._conn.close()
