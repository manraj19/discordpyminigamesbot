"""Gambling: wager coins on a coin flip or the slot machine."""

import random
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.games.gambling import slot_return, spin_slots


class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- coinflip ---
    def _coinflip(self, user, bet, side):
        side = side.lower()
        if side in ("h", "heads"):
            side = "heads"
        elif side in ("t", "tails"):
            side = "tails"
        else:
            return "Choose `heads` or `tails`."
        if bet <= 0:
            return "Your bet must be a positive number of coins."
        if not self.bot.economy.spend(user.id, bet):
            return "You don't have enough coins for that bet."
        result = random.choice(["heads", "tails"])
        if result == side:
            self.bot.economy.add_coins(user.id, str(user), bet * 2)
            return f"🪙 It landed **{result}** — you won **+{bet}** coins!"
        return f"🪙 It landed **{result}** — you lost **{bet}** coins."

    @commands.command(aliases=["cf"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx, bet: int, side: str = "heads"):
        await ctx.send(self._coinflip(ctx.author, bet, side))

    @app_commands.command(name="coinflip", description="Bet coins on a coin flip")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def coinflip_slash(
        self, interaction: discord.Interaction, bet: int, side: Literal["heads", "tails"] = "heads"
    ):
        await interaction.response.send_message(self._coinflip(interaction.user, bet, side))

    # --- slots ---
    def _slots(self, user, bet):
        if bet <= 0:
            return "Your bet must be a positive number of coins."
        if not self.bot.economy.spend(user.id, bet):
            return "You don't have enough coins for that bet."
        reels = spin_slots()
        line = " | ".join(reels)
        returned = slot_return(reels, bet)
        if returned > bet:
            self.bot.economy.add_coins(user.id, str(user), returned)
            return f"[ {line} ]\n🪙 Jackpot! You won **+{returned - bet}** coins."
        if returned == bet:
            self.bot.economy.add_coins(user.id, str(user), returned)
            return f"[ {line} ]\n🪙 Two of a kind — your **{bet}** coins are returned."
        return f"[ {line} ]\n🪙 No match. You lost **{bet}** coins."

    @commands.command(aliases=["slot"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def slots(self, ctx, bet: int):
        await ctx.send(self._slots(ctx.author, bet))

    @app_commands.command(name="slots", description="Bet coins on the slot machine")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def slots_slash(self, interaction: discord.Interaction, bet: int):
        await interaction.response.send_message(self._slots(interaction.user, bet))


async def setup(bot):
    await bot.add_cog(Gambling(bot))
