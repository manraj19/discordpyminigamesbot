"""Race - two players sprint to type each prompt word first."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import invalid_opponent

WORDS = [
    "go",
    "left",
    "right",
    "accelerate",
    "brake",
    "shift",
    "drift",
    "boost",
    "turbo",
    "nitro",
    "swerve",
    "throttle",
    "overtake",
    "corner",
]
ROUNDS = 7
ROUND_TIMEOUT = 10.0


class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _first_correct(self, check, word):
        """Return the first player to type ``word`` exactly, or None on timeout.
        Wrong answers are ignored so a typo doesn't waste the round."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + ROUND_TIMEOUT
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return None
            try:
                message = await self.bot.wait_for("message", check=check, timeout=remaining)
            except asyncio.TimeoutError:
                return None
            if message.content.lower().strip() == word:
                return message.author

    async def _play(self, channel, player1, player2):
        intro = discord.Embed(
            title="🏁 Race",
            description=(
                f"{player1.mention} vs {player2.mention}\n"
                f"First to type the word in **backticks** wins the round. Best of {ROUNDS}!"
            ),
            color=discord.Color.red(),
        )
        await channel.send(embed=intro)

        countdown = await channel.send("Starting in 3...")
        for n in (2, 1):
            await asyncio.sleep(1)
            await countdown.edit(content=f"Starting in {n}...")
        await asyncio.sleep(1)
        await countdown.edit(content="**GO!**")

        scores = {player1: 0, player2: 0}

        def check(m):
            return m.channel == channel and m.author in (player1, player2)

        for rnd in range(1, ROUNDS + 1):
            await asyncio.sleep(1)
            word = random.choice(WORDS)
            await channel.send(f"**Round {rnd}/{ROUNDS}** — type `{word}`!")
            winner = await self._first_correct(check, word)
            if winner is None:
                await channel.send(f"Nobody typed `{word}` in time! 😴")
            else:
                scores[winner] += 1
                await channel.send(f"✅ {winner.mention} got it!  **{scores[player1]}–{scores[player2]}**")

        if scores[player1] > scores[player2]:
            result = f"🏆 {player1.mention} wins the race!"
        elif scores[player2] > scores[player1]:
            result = f"🏆 {player2.mention} wins the race!"
        else:
            result = "It's a tie! 🤝"

        embed = discord.Embed(title="🏁 Race Results", color=discord.Color.gold())
        embed.add_field(name=player1.display_name, value=str(scores[player1]))
        embed.add_field(name=player2.display_name, value=str(scores[player2]))
        embed.add_field(name="Result", value=result, inline=False)
        await channel.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def race(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author, self_message="You cannot race against yourself!")
        if reason:
            await ctx.send(reason)
            return
        await self._play(ctx.channel, ctx.author, opponent)

    @app_commands.command(name="race", description="Race another user by typing words the fastest")
    @app_commands.describe(opponent="The member you want to race")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def race_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user, self_message="You cannot race against yourself!")
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return
        await interaction.response.send_message(f"🏁 Get ready, {interaction.user.mention} vs {opponent.mention}!")
        await self._play(interaction.channel, interaction.user, opponent)


async def setup(bot):
    await bot.add_cog(Race(bot))
