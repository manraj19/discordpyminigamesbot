"""Flagle - guess the country from its flag."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.data import COUNTRIES

GAME = "flagle"


class Flagle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _play(self, message, author, channel, send_text):
        score = 0
        response_time = 10.0
        embed = discord.Embed(title="Flagle Game", color=discord.Color.blue())

        while True:
            code = random.choice(list(COUNTRIES))
            name = COUNTRIES[code]
            flag_url = f"https://flagsapi.com/{code}/flat/64.png"
            # utcnow() is timezone-aware UTC; .timestamp() is correct provided
            # the host clock is synced (enable NTP on the droplet).
            deadline = round(discord.utils.utcnow().timestamp() + response_time)

            embed.clear_fields()
            embed.description = (
                f"Guess the country for this flag:\n[Flag Image]({flag_url})\n"
                f"You have until <t:{deadline}:R> to respond."
            )
            embed.set_image(url=flag_url)
            await message.edit(embed=embed)

            try:
                guess = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == author and m.channel == channel,
                    timeout=response_time,
                )
            except asyncio.TimeoutError:
                await send_text(f"Time's up! The correct answer was **{name}**. Your final score: {score}")
                break

            if guess.content.strip().lower() != name.lower():
                await send_text(f"Wrong! The correct answer was **{name}**. Your final score: {score}")
                break

            score += 1
            embed.clear_fields()
            embed.add_field(name="Result", value="Correct!", inline=False)
            embed.add_field(name="Score", value=str(score), inline=True)
            await message.edit(embed=embed)

        self.bot.scores.record_result(author.id, str(author), score, GAME)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def flagle(self, ctx):
        message = await ctx.send(embed=discord.Embed(title="Flagle Game", color=discord.Color.blue()))
        await self._play(message, ctx.author, ctx.channel, ctx.send)

    @app_commands.command(name="flagle", description="Guess the country based on its flag")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.user.id)
    async def flagle_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(title="Flagle Game", color=discord.Color.blue()))
        message = await interaction.original_response()
        await self._play(message, interaction.user, interaction.channel, interaction.followup.send)


async def setup(bot):
    await bot.add_cog(Flagle(bot))
