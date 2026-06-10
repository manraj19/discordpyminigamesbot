"""Blocklist persistence: users the owner has banned from using the bot.

Kept in the same ``scores.db`` file as a separate table. The set of blocked
IDs is cached in memory so the per-command check is a dict lookup, not a query.
"""

import datetime
import sqlite3


class BlocklistService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS blocklist (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                created_at TEXT
            )"""
        )
        self._conn.commit()
        self._cache = {row[0] for row in self._conn.execute("SELECT user_id FROM blocklist")}

    def is_blocked(self, user_id):
        return user_id in self._cache

    def add(self, user_id, reason=None):
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO blocklist (user_id, reason, created_at) VALUES (?, ?, ?)",
            (user_id, reason, created_at),
        )
        self._conn.commit()
        self._cache.add(user_id)

    def remove(self, user_id):
        self._conn.execute("DELETE FROM blocklist WHERE user_id = ?", (user_id,))
        self._conn.commit()
        self._cache.discard(user_id)

    def all(self):
        """Return [(user_id, reason), ...] ordered by when they were blocked."""
        cur = self._conn.execute("SELECT user_id, reason FROM blocklist ORDER BY created_at")
        return cur.fetchall()

    def close(self):
        self._conn.close()
