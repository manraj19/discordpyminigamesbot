"""Pure Blackjack logic (deck + hand values). No discord imports."""

import random


def create_deck():
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    return deck


def calculate_hand(hand):
    """Total a hand, demoting aces (11 -> 1) as needed to avoid busting."""
    total = sum(hand)
    aces = hand.count(11)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total
