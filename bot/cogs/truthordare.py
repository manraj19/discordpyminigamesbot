"""Truth or Dare command."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.views.truthordare import TruthOrDareView, random_question_embed


class TruthOrDare(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["tod"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def truthordare(self, ctx):
        view = TruthOrDareView()
        view.message = await ctx.send(embed=random_question_embed(), view=view)

    @app_commands.command(name="truthordare", description="Play a game of Truth or Dare")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def truthordare_slash(self, interaction: discord.Interaction):
        view = TruthOrDareView()
        await interaction.response.send_message(embed=random_question_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(TruthOrDare(bot))
