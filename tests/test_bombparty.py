"""Tests for the Bomb Party rules: judging, lives, turn order, alphabet bonus."""

import random

from bot.data import BOMB_PROMPTS, DICTIONARY
from bot.games.bombparty import (
    BONUS_LETTERS,
    HARD_FLOOR,
    MAX_LIVES,
    STARTING_LIVES,
    TURN_SECONDS_DECAY,
    TURN_SECONDS_MIN,
    TURN_SECONDS_START,
    accept,
    advance,
    alive,
    current_player,
    explode,
    judge,
    new_game,
    normalize,
    sample_prompt,
    turn_seconds,
    winner,
)


def _game(prompt="tra", players=(1, 2, 3)):
    game = new_game(players)
    game.prompt = prompt
    return game


# --- judging ---
def test_judge_accepts_a_real_word_containing_the_prompt():
    assert judge(_game(), "extra") == "ok"


def test_judge_rejects_a_word_without_the_prompt():
    assert judge(_game(), "hello") == "no_prompt"


def test_judge_rejects_something_that_is_not_a_word():
    assert judge(_game(), "tratra") == "not_a_word"


def test_judge_rejects_a_repeat():
    game = _game()
    accept(game, "extra")
    assert judge(game, "extra") == "used"


def test_normalize_strips_junk_and_blocks_non_letters():
    assert normalize("  ExTrA  ") == "extra"
    assert normalize("extra!") == ""  # punctuation is not a word
    assert normalize("🙂") == ""


# --- lives and elimination ---
def test_explosion_costs_a_life_then_knocks_you_out():
    game = _game()
    for _ in range(STARTING_LIVES - 1):
        assert explode(game) is False
    assert explode(game) is True  # the last life
    assert game.lives[1] == 0
    assert 1 not in alive(game)


def test_advance_skips_eliminated_players():
    game = _game()
    game.lives[2] = 0  # player 2 is out
    advance(game)
    assert current_player(game) == 3


def test_advance_wraps_and_counts_rounds():
    game = _game()
    for _ in range(len(game.players)):
        advance(game)
    assert current_player(game) == 1
    assert game.round == 2


def test_winner_is_none_until_one_is_left():
    game = _game()
    assert winner(game) is None
    game.lives[2] = 0
    assert winner(game) is None
    game.lives[3] = 0
    assert winner(game) == 1


# --- alphabet bonus ---
def test_alphabet_bonus_grants_one_life_and_resets():
    game = _game()
    game.lives[1] = 1  # room to grow
    game.letters[1] = set(BONUS_LETTERS) - {"a"}  # one letter short
    assert accept(game, "extra") is True  # supplies the missing "a"
    assert game.lives[1] == 2
    assert game.letters[1] == set()  # reset, so it has to be earned again


def test_alphabet_bonus_respects_the_life_cap():
    game = _game()
    game.lives[1] = MAX_LIVES
    game.letters[1] = set(BONUS_LETTERS) - {"a"}
    assert accept(game, "extra") is False  # already capped
    assert game.lives[1] == MAX_LIVES


def test_a_normal_word_does_not_grant_a_life():
    game = _game()
    assert accept(game, "extra") is False
    assert game.lives[1] == STARTING_LIVES


# --- the turn clock ---
def test_stalling_cannot_shorten_the_next_players_clock():
    """The bug that killed the shared fuse: a player sat on the bomb until it was
    nearly out, answered, and handed over a turn nobody could win. The clock now
    depends on the round alone, so burning your own turn costs the next player
    nothing."""
    game = _game()
    before = turn_seconds(game.round)
    advance(game)  # the player before you used every second they had
    assert turn_seconds(game.round) == before


def test_turn_clock_tightens_each_round_down_to_a_floor():
    assert turn_seconds(1) == TURN_SECONDS_START
    assert turn_seconds(2) == TURN_SECONDS_START - TURN_SECONDS_DECAY
    assert turn_seconds(500) == TURN_SECONDS_MIN
    clocks = [turn_seconds(r) for r in range(1, 40)]
    assert clocks == sorted(clocks, reverse=True)  # it never loosens again
    assert min(clocks) >= TURN_SECONDS_MIN  # and always leaves time to type


# --- prompts ---
def test_every_prompt_has_enough_words_behind_it():
    assert min(BOMB_PROMPTS.values()) >= HARD_FLOOR
    rng = random.Random(0)
    for round_no in (1, 5, 12):
        for _ in range(50):
            prompt = sample_prompt(rng, round_no)
            assert BOMB_PROMPTS[prompt] >= HARD_FLOOR


def test_prompts_get_rarer_as_rounds_pass():
    rng = random.Random(1)
    early = [BOMB_PROMPTS[sample_prompt(rng, 1)] for _ in range(200)]
    late = [BOMB_PROMPTS[sample_prompt(rng, 12)] for _ in range(200)]
    assert min(early) > min(late)


def test_sampled_prompts_are_answerable():
    """A prompt is only fair if a real dictionary word actually contains it."""
    rng = random.Random(2)
    for round_no in (1, 12):
        for _ in range(10):
            prompt = sample_prompt(rng, round_no)
            assert any(prompt in word for word in DICTIONARY)
