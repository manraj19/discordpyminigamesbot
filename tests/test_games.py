"""Unit tests for the pure game-logic modules (no Discord required)."""

from bot.games import blackjack, connect4
from bot.games.rps import winner


# --- Rock-Paper-Scissors ---
def test_rps_tie():
    assert winner("Rock", "Rock") is None


def test_rps_winner():
    assert winner("Rock", "Scissors") == "a"
    assert winner("Scissors", "Rock") == "b"
    assert winner("Paper", "Rock") == "a"


# --- Blackjack ---
def test_blackjack_deck_size_and_values():
    deck = blackjack.create_deck()
    assert len(deck) == 52
    assert deck.count(11) == 4  # four aces


def test_blackjack_aces_demote_to_avoid_bust():
    assert blackjack.calculate_hand([11, 11]) == 12  # one ace counts as 1
    assert blackjack.calculate_hand([11, 10]) == 21
    assert blackjack.calculate_hand([10, 10, 11]) == 21


# --- Connect 4 ---
def test_connect4_drop_lands_at_bottom():
    board = connect4.initialize_board()
    row = connect4.drop_piece(board, 3, connect4.PLAYER1_PIECE)
    assert row == connect4.ROWS - 1
    assert board[connect4.ROWS - 1][3] == connect4.PLAYER1_PIECE


def test_connect4_horizontal_win():
    board = connect4.initialize_board()
    for col in range(4):
        connect4.drop_piece(board, col, connect4.PLAYER1_PIECE)
    assert connect4.check_win(board, connect4.PLAYER1_PIECE)


def test_connect4_vertical_win():
    board = connect4.initialize_board()
    for _ in range(4):
        connect4.drop_piece(board, 2, connect4.PLAYER2_PIECE)
    assert connect4.check_win(board, connect4.PLAYER2_PIECE)


def test_connect4_no_false_win():
    board = connect4.initialize_board()
    connect4.drop_piece(board, 0, connect4.PLAYER1_PIECE)
    assert not connect4.check_win(board, connect4.PLAYER1_PIECE)
    assert not connect4.check_tie(board)
