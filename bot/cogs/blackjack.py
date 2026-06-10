"""Blackjack command."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.views.blackjack import BlackjackView


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["bj"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blackjack(self, ctx):
        view = BlackjackView(ctx.author)
        view.message = await ctx.send(embed=view.hidden_embed(), view=view)

    @app_commands.command(name="blackjack", description="Play a game of Blackjack against the bot")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def blackjack_slash(self, interaction: discord.Interaction):
        view = BlackjackView(interaction.user)
        await interaction.response.send_message(embed=view.hidden_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Blackjack(bot))
