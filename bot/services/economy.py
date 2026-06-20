"""Economy persistence: coin balances, the daily-claim streak, and cosmetic
titles bought from the shop.

Mirrors the other services - its own connection to ``scores.db`` and its own
tables. The streak/reward and per-game payout maths live in pure helpers
(``daily_outcome``, ``payout``) so they can be unit-tested without a database.
"""

import datetime
import sqlite3

BASE_DAILY = 100  # coins for a fresh claim
STREAK_BONUS = 25  # extra coins per consecutive day
STREAK_CAP_DAYS = 6  # bonus stops growing after a week (day 8+ = BASE + 6*BONUS)

# Game payouts (the "earn by playing" faucet). Win-based games record score 1 and
# pay WIN_COINS; score-based games pay per point so a bigger score earns more.
WIN_COINS = 15
PER_POINT = {"dino": 3, "mathematics": 5, "flagle": 8}

# Shop catalogue of cosmetic titles: id -> (display name, price in coins).
TITLES = {
    "novice": ("Novice", 100),
    "grinder": ("The Grinder", 500),
    "sharpshooter": ("Sharpshooter", 1000),
    "highroller": ("High Roller", 2500),
    "legend": ("Legend", 5000),
}


def daily_outcome(last_date, today, current_streak):
    """Pure daily-claim logic. Returns ``(claimed, new_streak, reward)``.

    ``claimed`` is False if the user already claimed today. Otherwise the streak
    grows by one on a consecutive day and resets to 1 after any gap (or the first
    ever claim), and the reward scales with the streak up to a weekly cap."""
    if last_date == today:
        return False, current_streak, 0
    if last_date is not None and (today - last_date).days == 1:
        new_streak = current_streak + 1
    else:
        new_streak = 1
    reward = BASE_DAILY + min(new_streak - 1, STREAK_CAP_DAYS) * STREAK_BONUS
    return True, new_streak, reward


def payout(game, score):
    """Coins earned for a game result. Pure so it can be tuned and tested."""
    if game in PER_POINT:
        return PER_POINT[game] * max(score, 0)
    return WIN_COINS if score > 0 else 0


class EconomyService:
    def __init__(self, db_path="scores.db"):
        self._conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS economy (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                coins INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                last_daily TEXT,
                title TEXT
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS cosmetics (
                user_id INTEGER,
                item_id TEXT,
                PRIMARY KEY (user_id, item_id)
            )"""
        )
        # Upgrade older economy tables that predate the cosmetics title column.
        cols = [r[1] for r in self._conn.execute("PRAGMA table_info(economy)")]
        if "title" not in cols:
            self._conn.execute("ALTER TABLE economy ADD COLUMN title TEXT")
        self._conn.commit()

    def balance(self, user_id):
        """Return ``(coins, streak)``; ``(0, 0)`` for a user with no row yet."""
        row = self._conn.execute("SELECT coins, streak FROM economy WHERE user_id = ?", (user_id,)).fetchone()
        return (row[0], row[1]) if row else (0, 0)

    def add_coins(self, user_id, username, amount):
        """Add coins (the payout faucet). Creates the row if needed."""
        self._conn.execute(
            "INSERT INTO economy (user_id, username, coins) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET username = excluded.username, coins = economy.coins + excluded.coins",
            (user_id, username, amount),
        )
        self._conn.commit()

    def spend(self, user_id, amount):
        """Deduct ``amount`` if the user can afford it. Returns True on success."""
        row = self._conn.execute("SELECT coins FROM economy WHERE user_id = ?", (user_id,)).fetchone()
        if row is None or row[0] < amount:
            return False
        self._conn.execute("UPDATE economy SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
        self._conn.commit()
        return True

    def top(self, limit=10):
        """Return [(username, coins), ...], richest first."""
        return self._conn.execute(
            "SELECT username, coins FROM economy ORDER BY coins DESC LIMIT ?", (limit,)
        ).fetchall()

    def claim_daily(self, user_id, username):
        """Try to claim the daily reward. Returns ``(claimed, reward, streak, coins)``;
        ``claimed`` is False (reward 0) if it was already claimed today."""
        cur = self._conn.cursor()
        row = cur.execute("SELECT coins, streak, last_daily FROM economy WHERE user_id = ?", (user_id,)).fetchone()
        today = datetime.datetime.now(datetime.timezone.utc).date()
        if row is None:
            coins, streak, last_date = 0, 0, None
        else:
            coins, streak, last_str = row
            last_date = datetime.date.fromisoformat(last_str) if last_str else None

        claimed, new_streak, reward = daily_outcome(last_date, today, streak)
        if not claimed:
            return False, 0, streak, coins

        coins += reward
        cur.execute(
            "INSERT INTO economy (user_id, username, coins, streak, last_daily) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET username = excluded.username, coins = excluded.coins, "
            "streak = excluded.streak, last_daily = excluded.last_daily",
            (user_id, username, coins, new_streak, today.isoformat()),
        )
        self._conn.commit()
        return True, reward, new_streak, coins

    # --- cosmetics (shop titles) ---
    def owns(self, user_id, item_id):
        return (
            self._conn.execute(
                "SELECT 1 FROM cosmetics WHERE user_id = ? AND item_id = ?", (user_id, item_id)
            ).fetchone()
            is not None
        )

    def owned_titles(self, user_id):
        return [r[0] for r in self._conn.execute("SELECT item_id FROM cosmetics WHERE user_id = ?", (user_id,))]

    def equipped_title(self, user_id):
        row = self._conn.execute("SELECT title FROM economy WHERE user_id = ?", (user_id,)).fetchone()
        return row[0] if row and row[0] else None

    def equip_title(self, user_id, item_id):
        self._conn.execute("UPDATE economy SET title = ? WHERE user_id = ?", (item_id, user_id))
        self._conn.commit()

    def buy_title(self, user_id, username, item_id):
        """Buy and equip a title. Returns 'bought', 'equipped' (already owned, just
        re-equipped, no charge), 'poor', or 'unknown'."""
        if item_id not in TITLES:
            return "unknown"
        if self.owns(user_id, item_id):
            self.equip_title(user_id, item_id)
            return "equipped"
        if not self.spend(user_id, TITLES[item_id][1]):
            return "poor"
        self._conn.execute("INSERT OR IGNORE INTO cosmetics (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
        self._conn.execute("UPDATE economy SET username = ? WHERE user_id = ?", (username, user_id))
        self._conn.commit()
        self.equip_title(user_id, item_id)
        return "bought"

    def close(self):
        self._conn.close()
