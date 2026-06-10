"""Dino Run - a chat-based reaction game."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands


class Dino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def dino(self, ctx):
        score = 0
        response_time = 8.0

        while True:
            obstacle = random.choice(["cactus", "bird"])
            end_time = discord.utils.utcnow().timestamp() + response_time
            if obstacle == "cactus":
                prompt = f"You're running towards a cactus. You have to respond <t:{int(end_time)}:R> (jump/duck)"
                correct = "jump"
            else:
                prompt = f"A bird is flying towards you. You have to respond <t:{int(end_time)}:R> (jump/duck)"
                correct = "duck"
            await ctx.send(prompt)

            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: (
                        m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["jump", "duck"]
                    ),
                    timeout=response_time,
                )
            except asyncio.TimeoutError:
                break

            if response.content.lower() != correct:
                break
            score += 1
            response_time = 1.8 if score >= 30 else max(2.0, response_time - 0.5)

        await ctx.send(f"Game over! Your final score is {score}.")
        self.bot.scores.record_result(ctx.author.id, str(ctx.author), score, "dino")

    @app_commands.command(name="dino", description="Play a game of Dino Run")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def dino_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🦖 Dino is a chat-based game — play it with `;dino`.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Dino(bot))
