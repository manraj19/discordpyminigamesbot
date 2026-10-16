"""Connect 4 view."""

import contextlib

import discord

from bot.games.connect4 import (
    COLUMNS,
    PLAYER1_PIECE,
    PLAYER2_PIECE,
    check_tie,
    check_win,
    column_full,
    drop_piece,
    initialize_board,
)


def _board_embed(board, current_player, piece):
    description = "\n".join("".join(row) for row in board)
    color = discord.Color.red() if piece == PLAYER1_PIECE else discord.Color.yellow()
    embed = discord.Embed(title="Connect 4", description=description, color=color)
    embed.add_field(name="Current Turn", value=f"{current_player.mention} ({piece})")
    return embed


class ColumnButton(discord.ui.Button):
    def __init__(self, col):
        super().__init__(label=str(col + 1), style=discord.ButtonStyle.primary)
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        await self.view.play(interaction, self.col)


class Connect4View(discord.ui.View):
    def __init__(self, player1, player2, *, on_win):
        super().__init__(timeout=60.0)
        self.player1 = player1
        self.player2 = player2
        self.board = initialize_board()
        self.current = player1
        self.on_win = on_win
        self.message = None
        for col in range(COLUMNS):
            self.add_item(ColumnButton(col))

    def _piece(self, player):
        return PLAYER1_PIECE if player == self.player1 else PLAYER2_PIECE

    def embed(self):
        return _board_embed(self.board, self.current, self._piece(self.current))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in (self.player1.id, self.player2.id):
            return True
        await interaction.response.send_message("This game isn't yours.", ephemeral=True)
        return False

    async def play(self, interaction, col):
        if interaction.user != self.current:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        if column_full(self.board, col):
            await interaction.response.send_message("This column is full! Choose another column.", ephemeral=True)
            return

        piece = self._piece(self.current)
        drop_piece(self.board, col, piece)

        if check_win(self.board, piece):
            line = (await self.on_win(self.current)).line()
            content = f"{self.current.mention} wins! 🎉" + (f"  ·  {line}" if line else "")
            await interaction.response.edit_message(content=content, embed=self.embed(), view=None)
            self.stop()
            return

        if check_tie(self.board):
            await interaction.response.edit_message(content="It's a tie! 😐", embed=self.embed(), view=None)
            self.stop()
            return

        if column_full(self.board, col):
            for item in self.children:
                if isinstance(item, ColumnButton) and item.col == col:
                    item.disabled = True

        self.current = self.player2 if self.current == self.player1 else self.player1
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_timeout(self):
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(
                    content=f"⌛ {self.current.mention} didn't move in time, so the game's over.",
                    embed=self.embed(),
                    view=None,
                )
