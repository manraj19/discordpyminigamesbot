"""Dino Run - a chat-based reaction game."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import emojis
from bot.core.utils import run_countdown

GAME = "dino"


class Dino(commands.Cog):
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
        score = 0
        response_time = 8.0

        while True:
            obstacle = random.choice(["cactus", "bird"])
            secs = int(response_time)
            if obstacle == "cactus":
                prefix = "You're running towards a cactus! Type `jump` or `duck`."
                correct = "jump"
            else:
                prefix = "A bird is flying towards you! Type `jump` or `duck`."
                correct = "duck"
            msg = await channel.send(f"{prefix}  ⏳ **{secs}s**")
            ticker = asyncio.create_task(run_countdown(msg, secs, prefix))

            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: (
                        m.author == player and m.channel == channel and m.content.lower() in ["jump", "duck"]
                    ),
                    timeout=response_time,
                )
            except asyncio.TimeoutError:
                break
            finally:
                ticker.cancel()

            if response.content.lower() != correct:
                break
            score += 1
            response_time = 1.8 if score >= 30 else max(2.0, response_time - 0.5)

        coins = self.bot.reward(player, score, GAME)
        await channel.send(f"Game over! Your final score is {score}. {emojis.COIN} **+{coins}** MiniCoins")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def dino(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="dino", description="Play a game of Dino Run")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def dino_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🦖 Dino Run! Get ready.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(Dino(bot))
