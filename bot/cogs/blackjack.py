"""Blackjack command."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.views.blackjack import BlackjackView


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _take_bet(self, user, bet):
        """Validate and deduct a wager. Returns an error string, or None if ok."""
        if bet < 0:
            return "Your bet can't be negative."
        if bet > 0 and not self.bot.economy.spend(user.id, bet):
            return "You don't have enough coins for that bet."
        return None

    @commands.command(aliases=["bj"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blackjack(self, ctx, bet: int = 0):
        error = self._take_bet(ctx.author, bet)
        if error:
            await ctx.send(error)
            return
        view = BlackjackView(ctx.author, bot=self.bot, bet=bet)
        view.message = await ctx.send(embed=view.hidden_embed(), view=view)

    @app_commands.command(name="blackjack", description="Play Blackjack against the bot (optionally wager coins)")
    @app_commands.describe(bet="Coins to wager (leave at 0 to play for fun)")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def blackjack_slash(self, interaction: discord.Interaction, bet: int = 0):
        error = self._take_bet(interaction.user, bet)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        view = BlackjackView(interaction.user, bot=self.bot, bet=bet)
        await interaction.response.send_message(embed=view.hidden_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
