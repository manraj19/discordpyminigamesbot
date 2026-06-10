"""Rock-Paper-Scissors command (prefix + slash share one starter)."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import invalid_opponent
from bot.views.rps import RPSView

GAME = "rockpaperscissors"


class RockPaperScissors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _record_win(self, member):
        self.bot.scores.record_result(member.id, str(member), 1, GAME)

    async def _start(self, send, player, opponent):
        view = RPSView(player, opponent, on_winner=self._record_win)
        view.message = await send(f"{player.mention} vs {opponent.mention}\nChoose your move!", view)

    @commands.command(name="rockpaperscissors", aliases=["rps"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def rps_prefix(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author)
        if reason:
            await ctx.send(reason)
            return

        async def send(content, view):
            return await ctx.send(content, view=view)

        await self._start(send, ctx.author, opponent)

    @app_commands.command(name="rockpaperscissors", description="Play a game of Rock-Paper-Scissors")
    @app_commands.describe(opponent="The member you want to play against")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def rps_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user)
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        async def send(content, view):
            await interaction.response.send_message(content, view=view)
            return await interaction.original_response()

        await self._start(send, interaction.user, opponent)


async def setup(bot):
    await bot.add_cog(RockPaperScissors(bot))
