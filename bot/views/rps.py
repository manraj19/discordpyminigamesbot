"""Rock-Paper-Scissors view. Both players pick privately; the result is
revealed once both have chosen. Scoring is injected via ``on_winner``."""

import contextlib

import discord

from bot.games.rps import winner


class RPSButton(discord.ui.Button):
    def __init__(self, choice):
        super().__init__(label=choice, style=discord.ButtonStyle.primary)
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        view: RPSView = self.view
        if interaction.user.id in view.choices:
            await interaction.response.send_message("You have already chosen!", ephemeral=True)
            return

        view.choices[interaction.user.id] = self.choice
        # Decided before the first await, so only the second pick can finish the game,
        # even when both players click within one round trip.
        last_pick = len(view.choices) == 2
        if last_pick:
            view.stop()
        await interaction.response.send_message(f"You chose {self.choice}.", ephemeral=True)
        if last_pick:
            await view.finish(interaction)


class RPSView(discord.ui.View):
    def __init__(self, player, opponent, *, on_winner):
        super().__init__(timeout=30.0)
        self.player = player
        self.opponent = opponent
        self.on_winner = on_winner  # async callable(winner, or None for a tie) -> RewardResult
        self.choices = {}
        self.message = None
        for choice in ("Rock", "Paper", "Scissors"):
            self.add_item(RPSButton(choice))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in (self.player.id, self.opponent.id):
            return True
        await interaction.response.send_message("This game isn't yours.", ephemeral=True)
        return False

    def _disable(self):
        for item in self.children:
            item.disabled = True

    async def finish(self, interaction):
        player_choice = self.choices[self.player.id]
        opponent_choice = self.choices[self.opponent.id]
        result = winner(player_choice, opponent_choice)
        champ = None if result is None else self.player if result == "a" else self.opponent
        line = (await self.on_winner(champ)).line()
        outcome = (f"{champ.mention} wins!" if champ else "It's a tie!") + (f"  ·  {line}" if line else "")

        self._disable()
        await interaction.followup.send(
            f"{self.player.mention} chose {player_choice}\n{self.opponent.mention} chose {opponent_choice}\n{outcome}"
        )
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)

    async def on_timeout(self):
        self._disable()
        late = " and ".join(p.mention for p in (self.player, self.opponent) if p.id not in self.choices)
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(content=f"⌛ {late} didn't pick in time, so the game's off.", view=self)
