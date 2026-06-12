"""Dino Run - a chat-based reaction game."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

GAME = "dino"


class Dino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, player):
        score = 0
        response_time = 8.0

        while True:
            obstacle = random.choice(["cactus", "bird"])
            # utcnow() is timezone-aware UTC, so .timestamp() is correct as long
            # as the host clock is synced (see deploy docs: enable NTP).
            deadline = round(discord.utils.utcnow().timestamp() + response_time)
            if obstacle == "cactus":
                prompt = f"You're running towards a cactus. Respond <t:{deadline}:R> — type `jump` or `duck`."
                correct = "jump"
            else:
                prompt = f"A bird is flying towards you. Respond <t:{deadline}:R> — type `jump` or `duck`."
                correct = "duck"
            await channel.send(prompt)

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

            if response.content.lower() != correct:
                break
            score += 1
            response_time = 1.8 if score >= 30 else max(2.0, response_time - 0.5)

        await channel.send(f"Game over! Your final score is {score}.")
        self.bot.scores.record_result(player.id, str(player), score, GAME)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def dino(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="dino", description="Play a game of Dino Run")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def dino_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🦖 **Dino Run** — get ready!")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(Dino(bot))
