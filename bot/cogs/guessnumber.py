"""Guess the Number - the classic higher/lower game over 1-1000."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

GAME = "guessnumber"
LOW, HIGH = 1, 1000
GUESS_TIMEOUT = 60.0


class GuessNumber(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, player):
        secret = random.randint(LOW, HIGH)
        await channel.send(f"🔢 I'm thinking of a number between **{LOW}** and **{HIGH}**. Start guessing!")

        attempts = 0
        while True:
            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: (
                        m.author == player and m.channel == channel and m.content.strip().lstrip("-").isdigit()
                    ),
                    timeout=GUESS_TIMEOUT,
                )
            except asyncio.TimeoutError:
                await channel.send(f"⏰ Time's up! The number was **{secret}**.")
                return

            attempts += 1
            guess = int(msg.content.strip())
            if guess == secret:
                tries = "guess" if attempts == 1 else "guesses"
                await channel.send(f"🎉 Got it in **{attempts}** {tries}! The number was **{secret}**.")
                self.bot.scores.record_result(player.id, str(player), 1, GAME)
                return
            await channel.send("Go higher ⬆️" if guess < secret else "Go lower ⬇️")

    @commands.command(aliases=["gn", "higherlower"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def guessnumber(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="guessnumber", description="Guess the number between 1 and 1000")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def guessnumber_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔢 Guess the Number! Between 1 and 1000.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(GuessNumber(bot))
