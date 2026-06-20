"""Tic-Tac-Toe command cog.

Demonstrates the target pattern: a single ``_start`` core drives both the
prefix command and the slash command, so the two stay in lockstep instead of
being copy-pasted (as they were in the monolith)."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import invalid_opponent
from bot.views.tictactoe import TicTacToeView

GAME = "tictactoe"


class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _record_win(self, member):
        return self.bot.reward(member, 1, GAME)

    async def _start(self, send, challenger, opponent):
        """Shared game starter. ``send(content, view)`` must send the message
        and return it, so prefix and slash can differ only in how they reply."""
        view = TicTacToeView(challenger, opponent, on_win=self._record_win)
        view.message = await send(
            f"{challenger.mention} vs {opponent.mention}\n{challenger.mention}, you're up first!",
            view,
        )

    @commands.command(name="tictactoe", aliases=["ttt"])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def tictactoe_prefix(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author)
        if reason:
            await ctx.send(reason)
            return

        async def send(content, view):
            return await ctx.send(content, view=view)

        await self._start(send, ctx.author, opponent)

    @app_commands.command(name="tictactoe", description="Play a game of Tic-Tac-Toe")
    @app_commands.describe(opponent="The member you want to play against")
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def tictactoe_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user)
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        async def send(content, view):
            await interaction.response.send_message(content, view=view)
            return await interaction.original_response()

        await self._start(send, interaction.user, opponent)


async def setup(bot):
    await bot.add_cog(TicTacToe(bot))
