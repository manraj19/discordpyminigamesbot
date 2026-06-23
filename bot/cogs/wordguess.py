"""Word Guess - guess the hidden 5-letter word in 6 tries (Wordle-style)."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import emojis
from bot.data import WORDS
from bot.games.wordguess import GREEN, is_valid_guess, score_guess

GAME = "wordguess"
MAX_TRIES = 6
GUESS_TIMEOUT = 120.0


class WordGuess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _board(guesses):
        return "\n".join(f"`{word.upper()}`  {''.join(tiles)}" for word, tiles in guesses)

    async def _is_word(self, word):
        # Same dictionary API as ;define. A reachable 404 means "not a word";
        # on any network error (status None) we allow the guess rather than punish it.
        # ponytail: one API call per guess, reuses http_client, no new dep.
        status, _ = await self.bot.http_client.fetch_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
        return status != 404

    async def _play(self, channel, player):
        if not self.bot.begin_session(player.id):
            await channel.send("⚠️ Finish your current game first.")
            return
        try:
            await self._run(channel, player)
        finally:
            self.bot.end_session(player.id)

    async def _run(self, channel, player):
        answer = random.choice(WORDS)
        intro = discord.Embed(
            title="🔤 Word Guess",
            description=(
                f"I'm thinking of a **5-letter word**. You have **{MAX_TRIES}** tries.\n"
                f"{GREEN} right letter, right spot · 🟨 right letter, wrong spot · ⬛ not in the word.\n\n"
                "Type your first guess!"
            ),
            color=discord.Color.blurple(),
        )
        await channel.send(embed=intro)

        guesses = []
        attempts = 0
        while attempts < MAX_TRIES:
            try:
                message = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == player and m.channel == channel,
                    timeout=GUESS_TIMEOUT,
                )
            except asyncio.TimeoutError:
                await channel.send(f"⏰ Time's up! The word was **{answer.upper()}**.")
                return

            guess = message.content.strip().lower()
            if not is_valid_guess(guess):
                await channel.send("❌ Please type a **5-letter word** (letters only).")
                continue
            if guess != answer and not await self._is_word(guess):
                await channel.send(f"❌ `{guess.upper()}` isn't a word. Try again (it won't cost a guess).")
                continue

            attempts += 1
            guesses.append((guess, score_guess(guess, answer)))
            board = self._board(guesses)

            if guess == answer:
                embed = discord.Embed(
                    title="🔤 Word Guess",
                    description=f"{board}\n\n🎉 **Solved in {attempts}/{MAX_TRIES}!**",
                    color=discord.Color.green(),
                )
                await channel.send(embed=embed)
                coins = self.bot.reward(player, 1, GAME)
                await channel.send(f"{emojis.COIN} **+{coins}** MiniCoins")
                return

            tries_left = MAX_TRIES - attempts
            if tries_left == 0:
                embed = discord.Embed(
                    title="🔤 Word Guess",
                    description=f"{board}\n\n😵 Out of tries! The word was **{answer.upper()}**.",
                    color=discord.Color.red(),
                )
                await channel.send(embed=embed)
                return

            embed = discord.Embed(
                title="🔤 Word Guess",
                description=f"{board}\n\n**{tries_left}** {'try' if tries_left == 1 else 'tries'} left.",
                color=discord.Color.blurple(),
            )
            await channel.send(embed=embed)

    @commands.command(aliases=["wg"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def wordguess(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="wordguess", description="Guess the hidden 5-letter word in 6 tries")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.user.id)
    async def wordguess_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔤 Word Guess! Find the 5-letter word.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(WordGuess(bot))
