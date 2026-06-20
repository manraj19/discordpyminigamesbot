"""Unscramble - rearrange the shuffled letters back into a real word."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import run_countdown
from bot.data import WORDS

GAME = "unscramble"
ROUND_SECONDS = 7


def scramble(word):
    """Shuffle a word's letters, retrying so we don't hand back the original.
    ponytail: gives up after a few tries for all-same-letter words (harmless)."""
    letters = list(word)
    for _ in range(10):
        random.shuffle(letters)
        if "".join(letters) != word:
            break
    return "".join(letters)


class Unscramble(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, player):
        answer = random.choice(WORDS).lower()
        secs = ROUND_SECONDS
        prefix = f"🔀 Unscramble this word: **{scramble(answer).upper()}**"
        msg = await channel.send(f"{prefix}  ⏳ **{secs}s**")
        ticker = asyncio.create_task(run_countdown(msg, secs, prefix))

        try:
            guess = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == player and m.channel == channel,
                timeout=float(secs),
            )
        except asyncio.TimeoutError:
            await channel.send(f"⏰ Time's up! The word was **{answer.upper()}**.")
            return
        finally:
            ticker.cancel()

        if guess.content.strip().lower() == answer:
            await channel.send(f"✅ Correct! It was **{answer.upper()}**.")
            coins = self.bot.reward(player, 1, GAME)
            await channel.send(f"🪙 **+{coins}** coins")
        else:
            await channel.send(f"❌ Nope, it was **{answer.upper()}**.")

    @commands.command(aliases=["scramble"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def unscramble(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="unscramble", description="Unscramble the shuffled letters into a word")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def unscramble_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔀 Unscramble! Find the word.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(Unscramble(bot))
