"""Gambling: wager coins on a coin flip or the slot machine."""

import asyncio
import random
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import emojis
from bot.games.gambling import slot_return, spin_slots

REVEAL_DELAY = 0.8  # seconds between each slot reel locking in


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
            return "Your bet must be a positive number of MiniCoins."
        if not self.bot.economy.spend(user.id, bet):
            return "You don't have enough MiniCoins for that bet."
        result = random.choice(["heads", "tails"])
        if result == side:
            self.bot.economy.add_coins(user.id, str(user), bet * 2)
            return f"{emojis.COIN} It landed **{result}**. You won **+{bet}** MiniCoins!"
        return f"{emojis.COIN} It landed **{result}**. You lost **{bet}** MiniCoins."

    @commands.command(aliases=["cf"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coinflip(self, ctx, bet: int, side: str):
        await ctx.send(self._coinflip(ctx.author, bet, side))

    @app_commands.command(name="coinflip", description="Bet MiniCoins on a coin flip")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def coinflip_slash(self, interaction: discord.Interaction, bet: int, side: Literal["heads", "tails"]):
        await interaction.response.send_message(self._coinflip(interaction.user, bet, side))

    # --- slots ---
    def _take_slots_bet(self, user, bet):
        if bet <= 0:
            return "Your bet must be a positive number of MiniCoins."
        if not self.bot.economy.spend(user.id, bet):
            return "You don't have enough MiniCoins for that bet."
        return None

    def _slots_outcome(self, user, bet, reels):
        returned = slot_return(reels, bet)
        if returned > bet:
            self.bot.economy.add_coins(user.id, str(user), returned)
            return f"{emojis.COIN} Jackpot! You won **+{returned - bet}** MiniCoins."
        if returned == bet:
            self.bot.economy.add_coins(user.id, str(user), returned)
            return f"{emojis.COIN} Two of a kind. Your **{bet}** MiniCoins come back."
        return f"{emojis.COIN} No match. You lost **{bet}** MiniCoins."

    async def _run_slots(self, user, bet, send):
        """Spin and reveal the reels one at a time for a bit of suspense. `send`
        posts the first message and returns it; the rest are edits."""
        error = self._take_slots_bet(user, bet)
        if error:
            await send(error)
            return
        reels = spin_slots()
        shown = ["❓", "❓", "❓"]
        message = await send(f"🎰  {'   '.join(shown)}")
        for i in range(3):
            await asyncio.sleep(REVEAL_DELAY)
            shown[i] = emojis.SLOT[reels[i]]
            await message.edit(content=f"🎰  {'   '.join(shown)}")
        await asyncio.sleep(0.4)
        result = self._slots_outcome(user, bet, reels)
        await message.edit(content=f"🎰  {'   '.join(shown)}\n{result}")

    @commands.command(aliases=["slot"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slots(self, ctx, bet: int):
        await self._run_slots(ctx.author, bet, ctx.send)

    @app_commands.command(name="slots", description="Bet MiniCoins on the slot machine")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def slots_slash(self, interaction: discord.Interaction, bet: int):
        async def send(content):
            await interaction.response.send_message(content)
            return await interaction.original_response()

        await self._run_slots(interaction.user, bet, send)


async def setup(bot):
    await bot.add_cog(Gambling(bot))
