"""Mathematics quiz - an escalating chat-based arithmetic game."""

import asyncio
import random
from typing import Literal

import discord
from discord import app_commands
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

    async def _play(self, channel, player, quiz_type):
        score = 0
        difficulty = 1
        response_time = 10.0

        while True:
            question, answer = _new_problem(quiz_type, difficulty)
            await channel.send(f"Solve: {question}\nYou have {int(response_time)} seconds to answer.")

            try:
                guess = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == player and m.channel == channel,
                    timeout=response_time,
                )
            except asyncio.TimeoutError:
                await channel.send(f"Time's up! The correct answer was {answer}. Your score is {score}")
                break

            try:
                if quiz_type == "division":
                    correct = abs(float(guess.content) - answer) < 0.01
                else:
                    correct = int(guess.content) == answer
            except ValueError:
                await channel.send(f"Invalid input! The correct answer was {answer}. Your score is {score}")
                break

            if not correct:
                await channel.send(f"Wrong! The correct answer was {answer}. Your score is {score}")
                break
            score += 1
            difficulty += 1
            response_time = max(5.0, response_time - 1.0)
            await channel.send("Correct!")

    @commands.command(aliases=["math", "maths"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def mathematics(self, ctx, quiz_type: str):
        quiz_type = quiz_type.lower()
        if quiz_type not in QUIZ_TYPES:
            await ctx.send("Invalid quiz type! Please choose from addition, subtraction, multiplication, or division.")
            return
        await self._play(ctx.channel, ctx.author, quiz_type)

    @app_commands.command(name="mathematics", description="Solve timed maths problems")
    @app_commands.describe(quiz_type="The kind of problems to solve")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def mathematics_slash(
        self,
        interaction: discord.Interaction,
        quiz_type: Literal["addition", "subtraction", "multiplication", "division"],
    ):
        await interaction.response.send_message(f"🧮 {quiz_type.capitalize()} quiz! Get ready.")
        await self._play(interaction.channel, interaction.user, quiz_type)


async def setup(bot):
    await bot.add_cog(Mathematics(bot))
