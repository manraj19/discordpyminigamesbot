"""Quest progress persistence, kept in scores.db.

Only progress is stored: which quests a user holds is recomputed from the seeded
pool (see ``bot.games.quests``), so there are no assignment rows to write. Each
row is one user's counter for one quest in one period, plus a ``claimed`` flag so
a finished quest pays its reward exactly once.

This layer never touches coins or XP. It advances counters, decides what just
completed, and hands that back; the bot credits the rewards through the reward
pipeline.
"""

import datetime
import sqlite3

from bot.games.quests import (
    DAILY_BONUS_COINS,
    DAILY_BONUS_ID,
    DAILY_BONUS_TEXT,
    DAILY_BONUS_XP,
    assign,
    period_key,
)


class QuestService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")  # concurrent readers with one writer, safer on crash
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS quests (
                user_id INTEGER,
                quest_id TEXT,
                period_key TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                claimed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, quest_id, period_key)
            )"""
        )
        self._conn.commit()

    def _row(self, user_id, quest_id, key):
        """Current ``(progress, claimed)`` for one quest, ``(0, False)`` if unseen."""
        row = self._conn.execute(
            "SELECT progress, claimed FROM quests WHERE user_id = ? AND quest_id = ? AND period_key = ?",
            (user_id, quest_id, key),
        ).fetchone()
        return (row[0], bool(row[1])) if row else (0, False)

    def _set(self, user_id, quest_id, key, progress, claimed):
        self._conn.execute(
            "INSERT INTO quests (user_id, quest_id, period_key, progress, claimed) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, quest_id, period_key) DO UPDATE SET "
            "progress = excluded.progress, claimed = excluded.claimed",
            (user_id, quest_id, key, progress, int(claimed)),
        )

    def progress(self, user_id, kind, amount, day=None):
        """Advance every active quest matching ``kind`` by ``amount``. Newly
        completed quests are marked claimed (so their reward pays once) and
        returned as ``[(text, coins, xp), ...]``, with the all-dailies bonus
        appended when the last daily lands. Crediting is the caller's job."""
        day = day or datetime.datetime.now(datetime.timezone.utc).date()
        completed = []
        for period in ("daily", "weekly"):
            key = period_key(period, day)
            quests = assign(user_id, period, key)
            for q in quests:
                if q.kind != kind:
                    continue
                prog, claimed = self._row(user_id, q.id, key)
                if claimed:
                    continue
                prog = min(prog + amount, q.target)
                done = prog >= q.target
                self._set(user_id, q.id, key, prog, done)
                if done:
                    completed.append((q.text, q.coins, q.xp))
            if period == "daily":
                bonus = self._claim_daily_bonus(user_id, key, quests)
                if bonus:
                    completed.append(bonus)
        self._conn.commit()
        return completed

    def _claim_daily_bonus(self, user_id, key, quests):
        """Pay the all-dailies bonus once, the moment every daily is claimed."""
        if self._row(user_id, DAILY_BONUS_ID, key)[1]:
            return None
        if not all(self._row(user_id, q.id, key)[1] for q in quests):
            return None
        self._set(user_id, DAILY_BONUS_ID, key, len(quests), True)
        return (DAILY_BONUS_TEXT, DAILY_BONUS_COINS, DAILY_BONUS_XP)

    def board(self, user_id, now=None):
        """The user's active quests for display. Returns
        ``{"daily": [(quest, progress, claimed), ...], "weekly": [...],
        "daily_bonus": bool}``."""
        now = now or datetime.datetime.now(datetime.timezone.utc)
        day = now.date()
        out = {}
        for period in ("daily", "weekly"):
            key = period_key(period, day)
            out[period] = [(q, *self._row(user_id, q.id, key)) for q in assign(user_id, period, key)]
        out["daily_bonus"] = self._row(user_id, DAILY_BONUS_ID, period_key("daily", day))[1]
        return out

    def close(self):
        self._conn.close()
