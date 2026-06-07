"""Pure Tic-Tac-Toe rules. No discord.py imports, so it can be unit-tested
in isolation. The Discord UI lives in ``bot.views.tictactoe`` and the command
wiring in ``bot.cogs.tictactoe``."""


class TicTacToeGame:
    EMPTY = " "

    def __init__(self):
        self.board = [[self.EMPTY] * 3 for _ in range(3)]
        self.current_symbol = "X"

    def is_available(self, row, col):
        return self.board[row][col] == self.EMPTY

    def play(self, row, col):
        """Place the current player's symbol at (row, col) and return it."""
        symbol = self.current_symbol
        self.board[row][col] = symbol
        return symbol

    def switch(self):
        self.current_symbol = "O" if self.current_symbol == "X" else "X"

    def _lines(self):
        b = self.board
        yield from b                                   # rows
        for c in range(3):                             # columns
            yield [b[0][c], b[1][c], b[2][c]]
        yield [b[0][0], b[1][1], b[2][2]]              # diagonals
        yield [b[0][2], b[1][1], b[2][0]]

    def winner(self):
        """Return the winning symbol ('X' or 'O'), or None."""
        for a, mid, c in self._lines():
            if a != self.EMPTY and a == mid == c:
                return a
        return None

    def is_full(self):
        return all(cell != self.EMPTY for row in self.board for cell in row)

    def is_draw(self):
        return self.is_full() and self.winner() is None
