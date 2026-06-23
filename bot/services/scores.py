"""Score persistence.

A single place for all reads/writes against ``scores.db``. Scores are tracked
per server (``guild_id``), so each guild has its own leaderboard; DMs fall into
bucket 0. An older global ``scores`` table is migrated into bucket 0 on startup.

NOTE: this is synchronous sqlite3 for now. SQLite writes are sub-millisecond at
this data size, so they don't meaningfully block the loop; migrating this class
to ``aiosqlite`` (or wrapping calls in ``asyncio.to_thread``) is the planned next
step and would not change its public interface.
"""

import sqlite3

# Games where only a personal best is kept; everything else accumulates.
NON_CUMULATIVE_GAMES = {"dino", "flagle", "mathematics"}

# Games that appear on leaderboards and profiles.
SUPPORTED_GAMES = [
    "dino",
    "flagle",
    "fight",
    "connect4",
    "rockpaperscissors",
    "tictactoe",
    "wordguess",
    "emojiguess",
    "mathematics",
    "unscramble",
    # guessnumber is deliberately omitted: its results are still written to
    # scores.db (so players count as registered users), but it stays off
    # leaderboards and profiles.
]

_SCHEMA = """CREATE TABLE {name} (
    user_id INTEGER,
    username TEXT,
    score INTEGER,
    game TEXT,
    guild_id INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, game, guild_id)
)"""


class ScoreService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute(_SCHEMA.format(name="IF NOT EXISTS scores"))
        cols = [r[1] for r in self._conn.execute("PRAGMA table_info(scores)")]
        if "guild_id" not in cols:
            # Upgrade a pre-per-server table; existing global rows go to bucket 0.
            self._conn.execute("ALTER TABLE scores RENAME TO scores_legacy")
            self._conn.execute(_SCHEMA.format(name="scores"))
            self._conn.execute(
                "INSERT INTO scores (user_id, username, score, game, guild_id) "
                "SELECT user_id, username, score, game, 0 FROM scores_legacy"
            )
            self._conn.execute("DROP TABLE scores_legacy")
        self._conn.commit()

    def record_result(self, user_id, username, score, game, guild_id=0):
        """Record a game result for a server: non-cumulative games keep the best
        score, others accumulate."""
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT score FROM scores WHERE user_id = ? AND game = ? AND guild_id = ?",
            (user_id, game, guild_id),
        ).fetchone()

        if row is None:
            cur.execute(
                "INSERT INTO scores (user_id, username, score, game, guild_id) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, score, game, guild_id),
            )
        elif game in NON_CUMULATIVE_GAMES:
            if score > row[0]:
                cur.execute(
                    "UPDATE scores SET score = ?, username = ? WHERE user_id = ? AND game = ? AND guild_id = ?",
                    (score, username, user_id, game, guild_id),
                )
        else:
            cur.execute(
                "UPDATE scores SET score = ?, username = ? WHERE user_id = ? AND game = ? AND guild_id = ?",
                (row[0] + score, username, user_id, game, guild_id),
            )
        self._conn.commit()

    def _agg(self, game):
        # Cumulative games sum across servers for a global view; best-score games
        # take the best single server result.
        return "MAX" if game in NON_CUMULATIVE_GAMES else "SUM"

    def top(self, game, guild_id=None, limit=10):
        """Top players for a game. ``guild_id=None`` aggregates globally across all
        servers; a guild_id returns that server's board."""
        if guild_id is None:
            return self._conn.execute(
                f"SELECT username, {self._agg(game)}(score) AS s FROM scores WHERE game = ? "
                "GROUP BY user_id ORDER BY s DESC LIMIT ?",
                (game, limit),
            ).fetchall()
        return self._conn.execute(
            "SELECT username, score FROM scores WHERE game = ? AND guild_id = ? ORDER BY score DESC LIMIT ?",
            (game, guild_id, limit),
        ).fetchall()

    def user_score(self, user_id, game, guild_id=None):
        """The user's score for a game, global (across servers) if guild_id is None."""
        if guild_id is None:
            row = self._conn.execute(
                f"SELECT {self._agg(game)}(score) FROM scores WHERE user_id = ? AND game = ?",
                (user_id, game),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT score FROM scores WHERE user_id = ? AND game = ? AND guild_id = ?",
                (user_id, game, guild_id),
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def rank(self, game, score, guild_id=None):
        """The 1-based rank a score would hold, global (across servers) if guild_id is None."""
        if guild_id is None:
            return self._conn.execute(
                f"SELECT COUNT(*) + 1 FROM (SELECT {self._agg(game)}(score) AS t FROM scores "
                "WHERE game = ? GROUP BY user_id) WHERE t > ?",
                (game, score),
            ).fetchone()[0]
        return self._conn.execute(
            "SELECT COUNT(*) + 1 FROM scores WHERE game = ? AND guild_id = ? AND score > ?",
            (game, guild_id, score),
        ).fetchone()[0]

    def total_user_score(self, user_id):
        """Sum of a user's scores across every game and server (for achievements)."""
        return self._conn.execute(
            "SELECT COALESCE(SUM(score), 0) FROM scores WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

    # --- global stats (across all servers) for the admin overview ---
    def count(self, game):
        return self._conn.execute("SELECT COUNT(*) FROM scores WHERE game = ?", (game,)).fetchone()[0]

    def total_entries(self):
        return self._conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]

    def unique_users(self):
        return self._conn.execute("SELECT COUNT(DISTINCT user_id) FROM scores").fetchone()[0]

    def close(self):
        self._conn.close()
