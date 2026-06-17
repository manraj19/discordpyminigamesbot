"""Tests for the word-guess tile scoring (the duplicate-letter rules)."""

from bot.games.wordguess import GRAY, GREEN, YELLOW, is_valid_guess, score_guess


def test_all_correct():
    assert score_guess("crane", "crane") == [GREEN] * 5


def test_none_present():
    assert score_guess("plumb", "crane") == [GRAY] * 5


def test_duplicate_letter_in_guess_single_in_answer():
    # "apple" has two p's at positions 1 and 2; guessing all p's should green
    # only those two and gray the rest.
    assert score_guess("ppppp", "apple") == [GRAY, GREEN, GREEN, GRAY, GRAY]


def test_mixed_greens_and_yellows():
    # guess "apple" vs answer "paper"
    assert score_guess("apple", "paper") == [YELLOW, YELLOW, GREEN, GRAY, YELLOW]


def test_case_insensitive():
    assert score_guess("CRANE", "crane") == [GREEN] * 5


def test_valid_guess():
    assert is_valid_guess("crane")
    assert not is_valid_guess("cran")  # too short
    assert not is_valid_guess("cranes")  # too long
    assert not is_valid_guess("cran3")  # not all letters
