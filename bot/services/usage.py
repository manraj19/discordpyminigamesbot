"""Command-usage counters, kept in scores.db.

Tallies how often each command runs per day, so the owner can see what players
actually use and tune payouts and the quest pool to match. Aggregated by day so
the table stays tiny regardless of traffic.
"""

import datetime
import sqlite3


class UsageService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS usage ("
            "day TEXT, command TEXT, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, command))"
        )
        self._conn.commit()

    def record(self, command, day=None):
        day = day or datetime.date.today().isoformat()
        self._conn.execute(
            "INSERT INTO usage (day, command, count) VALUES (?, ?, 1) "
            "ON CONFLICT(day, command) DO UPDATE SET count = count + 1",
            (day, command),
        )
        self._conn.commit()

    def _cutoff(self, days):
        return (datetime.date.today() - datetime.timedelta(days=days - 1)).isoformat()

    def top(self, days=7, limit=20):
        """Return [(command, total), ...] over the last ``days`` days, most used first."""
        return self._conn.execute(
            "SELECT command, SUM(count) AS total FROM usage WHERE day >= ? "
            "GROUP BY command ORDER BY total DESC LIMIT ?",
            (self._cutoff(days), limit),
        ).fetchall()

    def total(self, days=7):
        row = self._conn.execute("SELECT SUM(count) FROM usage WHERE day >= ?", (self._cutoff(days),)).fetchone()
        return row[0] or 0

    def close(self):
        self._conn.close()
