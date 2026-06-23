"""Rock-Paper-Scissors view. Both players pick privately; the result is
revealed once both have chosen. Scoring is injected via ``on_winner``."""

import discord

from bot.core import emojis
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
        await interaction.response.send_message(f"You chose {self.choice}.", ephemeral=True)
        if len(view.choices) == 2:
            await view.finish(interaction)


class RPSView(discord.ui.View):
    def __init__(self, player, opponent, *, on_winner=None):
        super().__init__(timeout=30.0)
        self.player = player
        self.opponent = opponent
        self.on_winner = on_winner
        self.choices = {}
        self.message = None
        for choice in ("Rock", "Paper", "Scissors"):
            self.add_item(RPSButton(choice))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in (self.player.id, self.opponent.id)

    async def finish(self, interaction):
        player_choice = self.choices[self.player.id]
        opponent_choice = self.choices[self.opponent.id]
        result = winner(player_choice, opponent_choice)

        if result is None:
            outcome = "It's a tie!"
        elif result == "a":
            coins = await self.on_winner(self.player) if self.on_winner else 0
            outcome = f"{self.player.mention} wins!" + (f"  ·  {emojis.COIN} +{coins} MiniCoins" if coins else "")
        else:
            coins = await self.on_winner(self.opponent) if self.on_winner else 0
            outcome = f"{self.opponent.mention} wins!" + (f"  ·  {emojis.COIN} +{coins} MiniCoins" if coins else "")

        for item in self.children:
            item.disabled = True
        await interaction.followup.send(
            f"{self.player.mention} chose {player_choice}\n{self.opponent.mention} chose {opponent_choice}\n{outcome}"
        )
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content="Time's up! The Rock-Paper-Scissors game has ended due to inactivity.",
                    view=self,
                )
            except discord.HTTPException:
                pass
        self.stop()
