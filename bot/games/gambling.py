"""Pure gambling maths: slot spins/payouts and blackjack bet settlement.

No discord imports, so the money logic can be unit-tested directly. The slot
table is tuned for a house edge (player gets back ~0.9x staked on average), so
slots drain coins rather than mint them."""

import random

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "💎", "7️⃣"]
# Three of a kind pays this multiple of the bet, per symbol (rarer = bigger).
TRIPLE_MULT = {"🍒": 3, "🍋": 5, "🔔": 8, "💎": 12, "7️⃣": 24}


def spin_slots():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]


def slot_return(reels, bet):
    """Coins returned for a spin. Three of a kind pays big; two of a kind returns
    the stake (a push); anything else loses the bet (returns 0)."""
    a, b, c = reels
    if a == b == c:
        return bet * TRIPLE_MULT[a]
    if a == b or b == c or a == c:
        return bet  # push - two matching gives the stake back
    return 0


def settle_blackjack(outcome, bet):
    """Coins to credit back for a blackjack result string. The stake was already
    taken at deal time, so a win returns 2x (net +bet) and a tie returns the bet."""
    o = outcome.lower()
    if "you win" in o:
        return bet * 2
    if "tie" in o:
        return bet
    return 0
