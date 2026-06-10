"""Score persistence.

A single place for all reads/writes against ``scores.db``, replacing the
scattered raw SQL and the fragile shared module-level cursor in the monolith.
Each call uses its own cursor, and the schema is unchanged so existing data
stays compatible.

NOTE: this is synchronous sqlite3 for now. SQLite writes are sub-millisecond
at this data size, so they don't meaningfully block the loop; migrating this
class to ``aiosqlite`` (or wrapping calls in ``asyncio.to_thread``) is the
planned next step and would not change its public interface.
"""

import sqlite3

# Games where only a personal best is kept; everything else accumulates.
NON_CUMULATIVE_GAMES = {"dino", "flagle"}

# Games that appear on leaderboards and profiles.
SUPPORTED_GAMES = ["dino", "flagle", "fight", "connect4", "rockpaperscissors", "tictactoe"]


class ScoreService:
    def __init__(self, db_path="scores.db"):
        # check_same_thread=False is safe here: discord.py runs on a single
        # event-loop thread, and a generous busy timeout absorbs brief locks
        # while the legacy connection still writes the not-yet-migrated games.
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS scores (
                user_id INTEGER,
                username TEXT,
                score INTEGER,
                game TEXT,
                PRIMARY KEY (user_id, game)
            )"""
        )
        self._conn.commit()

    def record_result(self, user_id, username, score, game):
        """Record a game result, preserving the monolith's semantics:
        non-cumulative games keep the best score, others accumulate."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT score FROM scores WHERE user_id = ? AND game = ?",
            (user_id, game),
        )
        row = cur.fetchone()

        if row is None:
            cur.execute(
                "INSERT INTO scores (user_id, username, score, game) VALUES (?, ?, ?, ?)",
                (user_id, username, score, game),
            )
        elif game in NON_CUMULATIVE_GAMES:
            if score > row[0]:
                cur.execute(
                    "UPDATE scores SET score = ? WHERE user_id = ? AND game = ?",
                    (score, user_id, game),
                )
        else:
            cur.execute(
                "UPDATE scores SET score = ? WHERE user_id = ? AND game = ?",
                (row[0] + score, user_id, game),
            )
        self._conn.commit()

    def top(self, game, limit=10):
        """Return [(username, score), ...] for a game, highest first."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT username, score FROM scores WHERE game = ? ORDER BY score DESC LIMIT ?",
            (game, limit),
        )
        return cur.fetchall()

    def user_score(self, user_id, game):
        """Return the user's score for a game, or None."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT score FROM scores WHERE user_id = ? AND game = ?",
            (user_id, game),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def rank(self, game, score):
        """Return the 1-based rank a given score would hold in a game."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT COUNT(*) + 1 FROM scores WHERE game = ? AND score > ?",
            (game, score),
        )
        return cur.fetchone()[0]

    def count(self, game):
        """Return how many entries exist for a game."""
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM scores WHERE game = ?", (game,))
        return cur.fetchone()[0]

    def close(self):
        self._conn.close()
