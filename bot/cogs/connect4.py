"""Connect 4 command."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import invalid_opponent
from bot.views.connect4 import Connect4View

GAME = "connect4"


class Connect4(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _record_win(self, member):
        return self.bot.reward(member, 1, GAME)

    async def _start(self, send, player, opponent):
        view = Connect4View(player, opponent, on_win=self._record_win)
        view.message = await send(embed=view.embed(), view=view)

    @commands.command(name="connect4", aliases=["c4"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def connect4_prefix(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author, self_message="You cannot play a game with yourself!")
        if reason:
            await ctx.send(reason)
            return

        async def send(**kwargs):
            return await ctx.send(**kwargs)

        await self._start(send, ctx.author, opponent)

    @app_commands.command(name="connect4", description="Play a game of Connect 4")
    @app_commands.describe(opponent="The member you want to play against")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def connect4_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user, self_message="You cannot play a game with yourself!")
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        async def send(**kwargs):
            await interaction.response.send_message(**kwargs)
            return await interaction.original_response()

        await self._start(send, interaction.user, opponent)


async def setup(bot):
    await bot.add_cog(Connect4(bot))
