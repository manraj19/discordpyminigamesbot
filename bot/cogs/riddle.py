"""Riddle - answer a random riddle within two minutes."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import RIDDLES


def _riddle_embed(question):
    embed = discord.Embed(title="Riddle Time!", description=question, color=discord.Color.blue())
    embed.set_footer(text="You have 2 minutes to answer.")
    return embed


class Riddle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def riddle(self, ctx):
        riddle = random.choice(RIDDLES)
        await ctx.send(embed=_riddle_embed(riddle["question"]))
        try:
            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            await ctx.send(f"Time's up! The correct answer was: {riddle['answer']}")
            return
        if message.content.strip().lower() == riddle["answer"]:
            await ctx.send("Correct! Well done!")
        else:
            await ctx.send(f"Incorrect! The correct answer was: {riddle['answer']}")

    @app_commands.command(name="riddle", description="Solve a riddle")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def riddle_slash(self, interaction: discord.Interaction):
        riddle = random.choice(RIDDLES)
        await interaction.response.send_message(embed=_riddle_embed(riddle["question"]))
        try:
            message = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == interaction.user and m.channel == interaction.channel,
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(f"Time's up! The correct answer was: {riddle['answer']}")
            return
        if message.content.strip().lower() == riddle["answer"]:
            await interaction.followup.send("Correct! Well done!")
        else:
            await interaction.followup.send(f"Incorrect! The correct answer was: {riddle['answer']}")


async def setup(bot):
    await bot.add_cog(Riddle(bot))
