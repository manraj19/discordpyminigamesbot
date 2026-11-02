"""Flagle - name as many flags as you can. Rules live in bot.games.flagle.

One message, edited once per flag. Listening starts before that edit goes out and
never waits on it, so a slow or rate limited edit can't swallow an answer, and each
flag's clock only starts once the flag is actually up.
"""

import asyncio
import contextlib
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import run_countdown
from bot.data import COUNTRIES
from bot.games.flagle import judge

GAME = "flagle"
ROUND_SECONDS = 10
# Discord takes about this long to draw a freshly edited image (0.5 to 1.5 seconds
# on the live bot). The clock waits it out, so the blank moment is on the house.
FLAG_LOAD_SECONDS = 1
# Ticking every second spends Discord's whole edit budget, which left the flag's own
# edit queueing behind the clock.
TICK_SECONDS = 2


def _flag_embed(code, title, status):
    embed = discord.Embed(title=title, description=status, color=discord.Color.blue())
    embed.set_image(url=f"https://flagcdn.com/w160/{code.lower()}.png")
    embed.set_footer(text="Typos are fine. Naming the wrong country ends the run.")
    return embed


class Flagle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, channel, author):
        await self.bot.play(channel, [author], lambda: self._run(channel, author))

    async def _clock(self, message, embed=None):
        """Put the flag up (the first one goes up with the message itself), then
        run its clock. Returning means time is up."""
        if embed is not None:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(content=f"⏳ **{ROUND_SECONDS}s**", embed=embed)
        await asyncio.sleep(FLAG_LOAD_SECONDS)
        await run_countdown(message, ROUND_SECONDS, step=TICK_SECONDS)

    async def _await_verdict(self, channel, author, clock, code, previous):
        """Read the player's messages until one decides this flag. Returns 'right',
        'wrong', or 'time' if the clock gets there first."""

        def mine(message):
            return message.author == author and message.channel == channel

        while True:
            waiter = asyncio.ensure_future(self.bot.wait_for("message", check=mine))
            await asyncio.wait({waiter, clock}, return_when=asyncio.FIRST_COMPLETED)
            if not waiter.done():
                waiter.cancel()
                return "time"
            guess = waiter.result()
            verdict = judge(guess.content, code, previous)
            if verdict in ("right", "wrong"):
                return verdict
            if verdict == "unknown":
                with contextlib.suppress(discord.HTTPException):
                    await guess.add_reaction("❓")

    async def _run(self, channel, author):
        score = 0
        message = previous = verdict = None

        for code in random.sample(list(COUNTRIES), len(COUNTRIES)):
            title = f"Flagle · Score {score}"
            if message is None:
                embed = _flag_embed(code, title, "Which country is this?")
                message = await channel.send(f"⏳ **{ROUND_SECONDS}s**", embed=embed)
                clock = asyncio.create_task(self._clock(message))
            else:
                embed = _flag_embed(code, title, f"✅ That was **{COUNTRIES[previous]}**. Next flag:")
                clock = asyncio.create_task(self._clock(message, embed))
            try:
                verdict = await self._await_verdict(channel, author, clock, code, previous)
            finally:
                clock.cancel()
            if verdict != "right":
                break
            score += 1
            previous = code

        # Pay first, so a failed message can't cost the player their run.
        result = self.bot.reward(author, score, GAME)
        name = COUNTRIES[code]
        ended = {"wrong": "Wrong! The correct answer", "time": "Time's up! The correct answer"}.get(verdict)
        final = _flag_embed(code, f"Flagle · Final score {score}", f"That was **{name}**.").remove_footer()
        with contextlib.suppress(discord.HTTPException):
            await message.edit(content="", embed=final)
        line = result.line() or "No MiniCoins this round."
        if ended:
            await channel.send(f"{ended} was **{name}**. Your final score: {score}\n{line}")
        else:
            await channel.send(f"That's every flag in the game. Your final score: {score}\n{line}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def flagle(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="flagle", description="Guess the country based on its flag")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def flagle_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚩 Flagle! Get ready.")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(Flagle(bot))
