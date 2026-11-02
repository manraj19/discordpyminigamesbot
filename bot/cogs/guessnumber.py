"""Guess the Number - the classic higher/lower game over 1-1000."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

GAME = "guessnumber"
LOW, HIGH = 1, 1000
MAX_TRIES = 10  # just enough for a clean binary search over 1-1000, so sloppy play can lose
GUESS_TIMEOUT = 60.0


def _is_guess(text):
    text = text.strip()
    return text.isdecimal() and LOW <= int(text) <= HIGH


class GuessNumber(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, player):
        await self.bot.play(channel, [player], lambda: self._run(channel, player))

    async def _run(self, channel, player):
        secret = random.randint(LOW, HIGH)
        await channel.send(
            f"🔢 I'm thinking of a number between **{LOW}** and **{HIGH}**. You get **{MAX_TRIES}** guesses. Go!"
        )

        for attempt in range(1, MAX_TRIES + 1):
            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == player and m.channel == channel and _is_guess(m.content),
                    timeout=GUESS_TIMEOUT,
                )
            except asyncio.TimeoutError:
                await channel.send(f"⏰ Time's up! The number was **{secret}**.")
                return

            guess = int(msg.content.strip())
            if guess == secret:
                tries = "guess" if attempt == 1 else "guesses"
                await channel.send(f"🎉 Got it in **{attempt}** {tries}! The number was **{secret}**.")
                result = self.bot.reward(player, 1, GAME)
                await channel.send(result.line())
                return
            if attempt < MAX_TRIES:
                hint = "Go higher ⬆️" if guess < secret else "Go lower ⬇️"
                await channel.send(f"{hint} · **{MAX_TRIES - attempt}** left")

        await channel.send(f"😵 Out of guesses! The number was **{secret}**.")

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
