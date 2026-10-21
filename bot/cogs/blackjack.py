"""Blackjack command."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.views.blackjack import BlackjackView


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _deal(self, user, bet):
        """Validate and take a wager, then deal. Returns ``(error, view)``; the view
        owns the stake from here and settles or refunds it."""
        if bet < 0:
            return "Your bet can't be negative.", None
        stake = None
        if bet > 0:
            stake = self.bot.economy.stake(user.id, str(user), bet, "blackjack")
            if stake is None:
                return "You don't have enough MiniCoins for that bet.", None
        return None, BlackjackView(user, bot=self.bot, bet=bet, stake=stake)

    @commands.command(aliases=["bj"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blackjack(self, ctx, bet: int = 0):
        error, view = self._deal(ctx.author, bet)
        if error:
            await ctx.send(error)
            return
        try:
            view.message = await ctx.send(embed=view.hidden_embed(), view=view)
        except discord.HTTPException:
            view.refund()  # the table never appeared, so the bet goes back
            raise

    @app_commands.command(name="blackjack", description="Play Blackjack against the bot (optionally wager MiniCoins)")
    @app_commands.describe(bet="MiniCoins to wager (leave at 0 to play for fun)")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def blackjack_slash(self, interaction: discord.Interaction, bet: int = 0):
        error, view = self._deal(interaction.user, bet)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return
        try:
            await interaction.response.send_message(embed=view.hidden_embed(), view=view)
        except discord.HTTPException:
            view.refund()
            raise
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
