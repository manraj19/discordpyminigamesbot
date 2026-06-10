"""Race - two players react to prompts; fastest correct answers win."""

import asyncio
import random

import discord
from discord.ext import commands

EVENTS = [
    ("There's a `right` turn coming up!", "right"),
    ("There's a `left` turn coming up!", "left"),
    ("Your opponent is catching up to you! `Accelerate` right now!", "accelerate"),
]


class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def race(self, ctx, opponent: discord.Member):
        if opponent == ctx.author:
            await ctx.send("You cannot race against yourself!")
            return
        if opponent.bot:
            await ctx.send("You cannot play against a bot!")
            return

        instructions = discord.Embed(
            title="Instructions",
            description="Type the words in `backticks` as fast as you can!",
            color=discord.Color.red(),
        )
        await ctx.send(embed=instructions)

        countdown = await ctx.send(f"Get ready to race {ctx.author.mention} and {opponent.mention}! (5 seconds)")
        for i in range(5, 0, -1):
            await countdown.edit(
                content=f"Get ready to race {ctx.author.mention} and {opponent.mention}! ({i} seconds)"
            )
            await asyncio.sleep(1)
        await ctx.send("The race has started! `Go`!")

        responses = {ctx.author: 0, opponent: 0}

        def check(m):
            return m.channel == ctx.channel and m.author in (ctx.author, opponent)

        async def award(expected, timeout):
            try:
                message = await self.bot.wait_for("message", timeout=timeout, check=check)
            except asyncio.TimeoutError:
                return
            if message.content.lower() == expected:
                responses[message.author] += 1

        await award("go", 5.0)

        for _ in range(5):
            await asyncio.sleep(5)
            event, expected = random.choice(EVENTS)
            await ctx.send(event)
            await award(expected, 3.0)

        await ctx.send("It's the final stretch! `Speed up` to win the race!")
        await award("speed up", 5.0)

        await asyncio.sleep(5)

        if responses[ctx.author] > responses[opponent]:
            winner = ctx.author
        elif responses[opponent] > responses[ctx.author]:
            winner = opponent
        else:
            winner = None

        result = discord.Embed(title="Race Results", color=discord.Color.random())
        if winner:
            result.add_field(name="Winner", value=winner.mention)
        else:
            result.add_field(name="Result", value="It's a tie!")
        result.add_field(name=f"{ctx.author.display_name}'s Responses", value=str(responses[ctx.author]))
        result.add_field(name=f"{opponent.display_name}'s Responses", value=str(responses[opponent]))
        await ctx.send(embed=result)


async def setup(bot):
    await bot.add_cog(Race(bot))
