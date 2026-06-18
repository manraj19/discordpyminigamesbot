"""Tests for the unscramble letter-shuffling helper."""

from collections import Counter

from bot.cogs.unscramble import scramble


def test_scramble_keeps_same_letters():
    assert Counter(scramble("crane")) == Counter("crane")


def test_scramble_changes_order():
    # A word with distinct letters should never come back unchanged.
    for _ in range(50):
        assert scramble("crane") != "crane"
