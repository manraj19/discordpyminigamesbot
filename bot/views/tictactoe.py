"""Discord UI for Tic-Tac-Toe. Holds the players/message and delegates all
rules to ``bot.games.tictactoe.TicTacToeGame``. Scoring is injected via an
``on_win`` coroutine so the view stays decoupled from persistence."""

import contextlib

import discord

from bot.games.tictactoe import TicTacToeGame


class TicTacToeButton(discord.ui.Button):
    def __init__(self, row, col):
        # Label e.g. "A1".. matches the original board layout.
        super().__init__(label=f"{chr(65 + row)}{col + 1}", style=discord.ButtonStyle.secondary)
        self._row = row
        self._col = col

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view

        if interaction.user != view.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        if not view.game.is_available(self._row, self._col):
            await interaction.response.send_message("This tile is already taken!", ephemeral=True)
            return

        symbol = view.game.play(self._row, self._col)
        self.label = symbol
        self.style = discord.ButtonStyle.primary if symbol == "X" else discord.ButtonStyle.danger
        self.disabled = True
        await interaction.response.edit_message(view=view)

        if view.game.winner() is not None:
            view.disable_all()
            line = (await view.on_win(interaction.user)).line()
            text = f"{interaction.user.mention} wins! 🎉" + (f"  ·  {line}" if line else "")
            await view.message.edit(content=text, view=view)
            view.stop()
            return

        if view.game.is_draw():
            view.disable_all()
            await view.message.edit(content="It's a draw! 😐", view=view)
            view.stop()
            return

        view.switch_player()
        await view.message.edit(content=f"It's {view.current_player.mention}'s turn!", view=view)


class TicTacToeView(discord.ui.View):
    def __init__(self, player1, player2, *, on_win):
        super().__init__(timeout=30.0)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.game = TicTacToeGame()
        self.message = None
        self.on_win = on_win  # async callable(member) -> RewardResult
        for row in range(3):
            for col in range(3):
                self.add_item(TicTacToeButton(row, col))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in (self.player1.id, self.player2.id):
            return True
        await interaction.response.send_message("This game isn't yours.", ephemeral=True)
        return False

    def switch_player(self):
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        self.game.switch()

    def disable_all(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        self.disable_all()
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(
                    content=f"⌛ {self.current_player.mention} didn't move in time, so the game's over.", view=self
                )
