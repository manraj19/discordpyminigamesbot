"""Tests for the blocklist service (uses an in-memory database)."""

from bot.services.blocklist import BlocklistService


def test_blocklist_add_check_remove():
    bl = BlocklistService(":memory:")
    try:
        assert not bl.is_blocked(123)

        bl.add(123, "spamming")
        assert bl.is_blocked(123)
        assert bl.all() == [(123, "spamming")]

        bl.remove(123)
        assert not bl.is_blocked(123)
        assert bl.all() == []
    finally:
        bl.close()


def test_blocklist_add_is_idempotent():
    bl = BlocklistService(":memory:")
    try:
        bl.add(1)
        bl.add(1, "updated reason")
        assert bl.all() == [(1, "updated reason")]
        assert bl.is_blocked(1)
    finally:
        bl.close()
