"""The one way a service opens ``scores.db``."""

import sqlite3


def connect(db_path):
    """A connection for one service. They all share one database, so each gets WAL
    (readers don't block the writer) and a long timeout rather than failing on a
    busy write.

    synchronous=NORMAL takes a game reward from 23 ms of blocking the event loop to
    under 1 ms. In WAL mode it can't corrupt the file; a power cut can lose the last
    few commits, which is a fair trade for a game bot."""
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn
