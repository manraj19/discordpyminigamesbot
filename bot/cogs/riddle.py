"""Riddle - solve a random riddle, with hints and forgiving answer matching."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import RIDDLES
from bot.games.riddle import is_correct

RIDDLE_TIME = 60.0


class Riddle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, player):
        if not self.bot.begin_session(player.id):
            await channel.send("⚠️ Finish your current game first.")
            return
        try:
            await self._run(channel, player)
        finally:
            self.bot.end_session(player.id)

    async def _run(self, channel, player):
        riddle = random.choice(RIDDLES)
        question, answer = riddle["question"], riddle["answer"]

        embed = discord.Embed(title="🧩 Riddle Time!", description=question, color=discord.Color.blurple())
        embed.set_footer(text=f"You have {int(RIDDLE_TIME)} seconds, and you can guess as many times as you like.")
        await channel.send(embed=embed)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + RIDDLE_TIME
        attempts = 0

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                await channel.send(f"⏰ Time's up! The answer was **{answer}**.")
                return
            try:
                message = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == player and m.channel == channel,
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                await channel.send(f"⏰ Time's up! The answer was **{answer}**.")
                return

            if is_correct(message.content, answer):
                await channel.send(f"✅ Correct, {player.mention}! The answer was **{answer}**.")
                return

            attempts += 1
            if attempts == 2:
                letters = len(answer.replace(" ", ""))
                await channel.send(
                    f"❌ Not quite! Hint: it starts with **{answer[0].upper()}** and has **{letters}** letters. Keep trying!"
                )
            else:
                await channel.send("❌ Not quite, try again!")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def riddle(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="riddle", description="Solve a riddle")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def riddle_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🧩 Here's your riddle.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(Riddle(bot))
