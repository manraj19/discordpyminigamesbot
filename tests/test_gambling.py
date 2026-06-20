"""Tests for the gambling payout maths (slots and blackjack settlement)."""

from bot.games.gambling import TRIPLE_MULT, settle_blackjack, slot_return


def test_slot_three_of_a_kind_pays_per_symbol():
    assert slot_return(["7️⃣", "7️⃣", "7️⃣"], 10) == 10 * TRIPLE_MULT["7️⃣"]
    assert slot_return(["🍒", "🍒", "🍒"], 10) == 10 * TRIPLE_MULT["🍒"]


def test_slot_pair_returns_the_stake():
    assert slot_return(["🍒", "🍒", "🍋"], 10) == 10
    assert slot_return(["🍋", "🍒", "🍒"], 10) == 10


def test_slot_no_match_loses_bet():
    assert slot_return(["🍒", "🍋", "🔔"], 10) == 0


def test_slot_has_house_edge():
    # Average return over every possible spin should be below the stake, so slots
    # drain coins rather than mint them.
    from itertools import product

    from bot.games.gambling import SLOT_SYMBOLS

    spins = list(product(SLOT_SYMBOLS, repeat=3))
    avg = sum(slot_return(list(r), 100) for r in spins) / len(spins)
    assert avg < 100


def test_blackjack_settlement():
    assert settle_blackjack("You win!", 50) == 100  # win returns 2x (net +50)
    assert settle_blackjack("It's a tie.", 50) == 50  # push returns the stake
    assert settle_blackjack("Dealer wins.", 50) == 0  # loss returns nothing
    assert settle_blackjack("You busted! Dealer wins.", 50) == 0
