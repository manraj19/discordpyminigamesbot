"""Disabled-channel persistence: channels where the bot is turned off.

Kept in the same ``scores.db`` file as a separate table. The set of disabled
channel IDs is cached in memory so the per-command check is a dict lookup, not a
query.
"""

import sqlite3


class ChannelLockService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute("CREATE TABLE IF NOT EXISTS disabled_channels (channel_id INTEGER PRIMARY KEY)")
        self._conn.commit()
        self._cache = {row[0] for row in self._conn.execute("SELECT channel_id FROM disabled_channels")}

    def is_disabled(self, channel_id):
        return channel_id in self._cache

    def disable(self, channel_id):
        self._conn.execute("INSERT OR IGNORE INTO disabled_channels (channel_id) VALUES (?)", (channel_id,))
        self._conn.commit()
        self._cache.add(channel_id)

    def enable(self, channel_id):
        self._conn.execute("DELETE FROM disabled_channels WHERE channel_id = ?", (channel_id,))
        self._conn.commit()
        self._cache.discard(channel_id)

    def all(self):
        return sorted(self._cache)

    def close(self):
        self._conn.close()
