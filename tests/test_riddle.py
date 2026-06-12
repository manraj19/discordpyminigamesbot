"""Tests for the forgiving riddle answer matching."""

from bot.games.riddle import is_correct, normalize


def test_normalize_strips_article_and_punctuation():
    assert normalize("A piano!") == "piano"
    assert normalize("the Map.") == "map"


def test_exact_and_article_and_case_insensitive():
    assert is_correct("piano", "piano")
    assert is_correct("a piano", "piano")
    assert is_correct("PIANO", "piano")


def test_answer_within_a_sentence():
    assert is_correct("it's a piano", "piano")
    assert is_correct("i think the answer is an echo", "echo")


def test_multiword_answer():
    assert is_correct("a pine tree", "pine tree")
    assert is_correct("garbage truck", "garbage truck")


def test_wrong_answers_rejected():
    assert not is_correct("guitar", "piano")
    assert not is_correct("", "piano")


def test_short_answer_requires_whole_word():
    # answer "m" must not match any word that merely contains an 'm'
    assert not is_correct("maximum", "m")
    assert is_correct("m", "m")
