"""Magic 8-ball."""

import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import EIGHT_BALL

QUESTION_LIMIT = 1900  # a message tops out at 2000 characters


def _question_line(question):
    return f"**Question:** {question[:QUESTION_LIMIT]}\n**Answer:**"


def _answer_embed():
    return discord.Embed(title=random.choice(EIGHT_BALL), color=discord.Colour.random())


class EightBall(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="8ball")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def eight_ball(self, ctx, *, question):
        await ctx.send(content=_question_line(question), embed=_answer_embed())

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="The question you want to ask the magic 8-ball")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def eight_ball_slash(self, interaction: discord.Interaction, question: str):
        await interaction.response.send_message(content=_question_line(question), embed=_answer_embed())


async def setup(bot):
    await bot.add_cog(EightBall(bot))
