"""Pure Connect 4 board logic. No discord imports."""

EMPTY_SLOT = "⚪"
PLAYER1_PIECE = "🔴"
PLAYER2_PIECE = "🟡"
ROWS = 6
COLUMNS = 7


def initialize_board():
    return [[EMPTY_SLOT for _ in range(COLUMNS)] for _ in range(ROWS)]


def column_full(board, col):
    return board[0][col] != EMPTY_SLOT


def drop_piece(board, col, piece):
    """Drop ``piece`` into ``col``; return the row it landed in, or None if full."""
    for row in reversed(range(ROWS)):
        if board[row][col] == EMPTY_SLOT:
            board[row][col] = piece
            return row
    return None


def check_win(board, piece):
    for row in range(ROWS):
        for col in range(COLUMNS - 3):
            if all(board[row][col + i] == piece for i in range(4)):
                return True
    for row in range(ROWS - 3):
        for col in range(COLUMNS):
            if all(board[row + i][col] == piece for i in range(4)):
                return True
    for row in range(ROWS - 3):
        for col in range(COLUMNS - 3):
            if all(board[row + i][col + i] == piece for i in range(4)):
                return True
    for row in range(3, ROWS):
        for col in range(COLUMNS - 3):
            if all(board[row - i][col + i] == piece for i in range(4)):
                return True
    return False


def check_tie(board):
    return all(board[row][col] != EMPTY_SLOT for row in range(ROWS) for col in range(COLUMNS))
