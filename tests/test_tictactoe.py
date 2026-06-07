"""Unit tests for the pure Tic-Tac-Toe rules. No Discord required - this is
the payoff of keeping game logic free of discord.py imports."""

from bot.games.tictactoe import TicTacToeGame


def test_new_game_is_empty_and_x_starts():
    game = TicTacToeGame()
    assert game.current_symbol == "X"
    assert all(game.is_available(r, c) for r in range(3) for c in range(3))
    assert game.winner() is None
    assert not game.is_draw()


def test_play_places_symbol_and_marks_unavailable():
    game = TicTacToeGame()
    assert game.play(0, 0) == "X"
    assert not game.is_available(0, 0)


def test_switch_alternates_symbol():
    game = TicTacToeGame()
    game.switch()
    assert game.current_symbol == "O"
    game.switch()
    assert game.current_symbol == "X"


def test_row_win():
    game = TicTacToeGame()
    game.board[1] = ["X", "X", "X"]
    assert game.winner() == "X"


def test_column_win():
    game = TicTacToeGame()
    for r in range(3):
        game.board[r][2] = "O"
    assert game.winner() == "O"


def test_diagonal_wins():
    game = TicTacToeGame()
    game.board[0][0] = game.board[1][1] = game.board[2][2] = "X"
    assert game.winner() == "X"

    other = TicTacToeGame()
    other.board[0][2] = other.board[1][1] = other.board[2][0] = "O"
    assert other.winner() == "O"


def test_full_board_with_no_line_is_draw():
    game = TicTacToeGame()
    game.board = [
        ["X", "O", "X"],
        ["X", "O", "O"],
        ["O", "X", "X"],
    ]
    assert game.is_full()
    assert game.winner() is None
    assert game.is_draw()
