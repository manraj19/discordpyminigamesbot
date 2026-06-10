"""Mathematics quiz - an escalating chat-based arithmetic game."""

import asyncio
import random

import discord
from discord.ext import commands

QUIZ_TYPES = ["addition", "subtraction", "multiplication", "division"]


def _new_problem(quiz_type, difficulty):
    if quiz_type == "addition":
        a, b = random.randint(1, 10 * difficulty), random.randint(1, 10 * difficulty)
        return f"{a} + {b}", a + b
    if quiz_type == "subtraction":
        a, b = random.randint(1, 10 * difficulty), random.randint(1, 10 * difficulty)
        return f"{a} - {b}", a - b
    if quiz_type == "multiplication":
        a, b = random.randint(1, 5 * difficulty), random.randint(1, 5 * difficulty)
        return f"{a} * {b}", a * b
    b = random.randint(1, 5 * difficulty)
    a = b * random.randint(1, 5 * difficulty)
    return f"{a} / {b}", round(a / b, 2)


class Mathematics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["math", "maths"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def mathematics(self, ctx, quiz_type: str):
        quiz_type = quiz_type.lower()
        if quiz_type not in QUIZ_TYPES:
            await ctx.send("Invalid quiz type! Please choose from addition, subtraction, multiplication, or division.")
            return

        score = 0
        difficulty = 1
        response_time = 10.0

        while True:
            question, answer = _new_problem(quiz_type, difficulty)
            end_time = discord.utils.utcnow().timestamp() + response_time
            await ctx.send(f"Solve: {question}\nYou have to answer <t:{int(end_time)}:R>.")

            try:
                guess = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                    timeout=response_time,
                )
            except asyncio.TimeoutError:
                await ctx.send(f"Time's up! The correct answer was {answer}. Your score is {score}")
                break

            try:
                if quiz_type == "division":
                    correct = abs(float(guess.content) - answer) < 0.01
                else:
                    correct = int(guess.content) == answer
            except ValueError:
                await ctx.send(f"Invalid input! The correct answer was {answer}. Your score is {score}")
                break

            if not correct:
                await ctx.send(f"Wrong! The correct answer was {answer}. Your score is {score}")
                break
            score += 1
            difficulty += 1
            response_time = max(5.0, response_time - 1.0)
            await ctx.send("Correct!")


async def setup(bot):
    await bot.add_cog(Mathematics(bot))
