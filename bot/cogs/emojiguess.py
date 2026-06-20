"""Emoji Guess - work out the word or phrase from a string of emojis."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import EMOJI_PUZZLES
from bot.games.riddle import is_correct

GAME = "emojiguess"
ROUND_TIME = 60.0


class EmojiGuess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, player):
        puzzle = random.choice(EMOJI_PUZZLES)
        clue, answer = puzzle["clue"], puzzle["answer"]

        embed = discord.Embed(
            title="😀 Emoji Guess",
            description=f"# {clue}\n\nWhat word or phrase is this?",
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"You have {int(ROUND_TIME)} seconds. Multiple guesses allowed!")
        await channel.send(embed=embed)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + ROUND_TIME
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
                await channel.send(f"✅ Correct, {player.mention}! It was **{answer}**.")
                coins = self.bot.reward(player, 1, GAME)
                await channel.send(f"🪙 **+{coins}** coins")
                return

            attempts += 1
            if attempts == 2:
                words = answer.split()
                shape = " ".join("_" * len(w) for w in words)
                await channel.send(
                    f"❌ Not quite! Hint: it starts with **{answer[0].upper()}** and looks like `{shape}`."
                )
            else:
                await channel.send("❌ Not quite, try again!")

    @commands.command(aliases=["emoji"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def emojiguess(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="emojiguess", description="Guess the word or phrase from emojis")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def emojiguess_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("😀 Emoji Guess! Decode the emojis.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(EmojiGuess(bot))
