"""Channel rules, kept in the same ``scores.db`` file.

- Disabled channels: where a server admin (or the owner) turned the bot off with ``;disable``.
- Game channels: games a server admin pinned to channels with ``;setchannel``.

Both are cached in memory, so the per-command check is a dict lookup, not a
query.
"""

import sqlite3


class ChannelLockService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")  # concurrent readers with one writer, safer on crash
        self._conn.execute("CREATE TABLE IF NOT EXISTS disabled_channels (channel_id INTEGER PRIMARY KEY)")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS game_channels ("
            "guild_id INTEGER, game TEXT, channel_id INTEGER, PRIMARY KEY (game, channel_id))"
        )
        self._conn.commit()
        self._cache = {row[0] for row in self._conn.execute("SELECT channel_id FROM disabled_channels")}
        self._games = {}  # guild id -> {game: {channel ids}}
        for guild_id, game, channel_id in self._conn.execute("SELECT guild_id, game, channel_id FROM game_channels"):
            self._games.setdefault(guild_id, {}).setdefault(game, set()).add(channel_id)

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

    # --- games pinned to channels (;setchannel) ---
    def game_channels(self, guild_id):
        """A server's pins as ``{game: {channel ids}}``. Treat it as read only."""
        return self._games.get(guild_id, {})

    def pin_game(self, guild_id, game, channel_id):
        self._conn.execute(
            "INSERT OR IGNORE INTO game_channels (guild_id, game, channel_id) VALUES (?, ?, ?)",
            (guild_id, game, channel_id),
        )
        self._conn.commit()
        self._games.setdefault(guild_id, {}).setdefault(game, set()).add(channel_id)

    def unpin_game(self, guild_id, game, channel_id=None):
        """Unpin a game from one channel, or from every channel when ``channel_id``
        is None. Returns how many pins were removed."""
        pins = self._games.get(guild_id, {})
        homes = pins.get(game, set())
        gone = set(homes) if channel_id is None else homes & {channel_id}
        self._conn.executemany("DELETE FROM game_channels WHERE game = ? AND channel_id = ?", [(game, c) for c in gone])
        self._conn.commit()
        homes -= gone
        if not homes:
            pins.pop(game, None)
        return len(gone)

    def unpin_channel(self, guild_id, channel_id):
        """Unpin every game from a channel. Returns how many pins were removed."""
        return sum(self.unpin_game(guild_id, game, channel_id) for game in list(self.game_channels(guild_id)))

    def close(self):
        self._conn.close()
