"""Economy: a daily coin claim with a streak, a balance check, and a small
cosmetic-title shop that coins are spent on."""

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.services.economy import TITLES

TitleId = Literal["novice", "grinder", "sharpshooter", "highroller", "legend"]


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- daily ---
    def _claim(self, user):
        claimed, reward, streak, coins = self.bot.economy.claim_daily(user.id, str(user))
        if not claimed:
            return discord.Embed(
                title="🪙 Daily already claimed",
                description=f"Come back tomorrow! 🔥 **{streak}**-day streak · balance **{coins}** coins.",
                color=discord.Color.orange(),
            )
        return discord.Embed(
            title="🪙 Daily reward claimed!",
            description=f"+**{reward}** coins · 🔥 **{streak}**-day streak · balance **{coins}** coins.",
            color=discord.Color.gold(),
        )

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily(self, ctx):
        await ctx.send(embed=self._claim(ctx.author))

    @app_commands.command(name="daily", description="Claim your daily coins and keep your streak alive")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def daily_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._claim(interaction.user))

    # --- balance ---
    @commands.command(aliases=["bal", "coins"])
    async def balance(self, ctx):
        coins, _ = self.bot.economy.balance(ctx.author.id)
        await ctx.send(f"🪙 **{coins}** coins")

    @app_commands.command(name="balance", description="Check your coin balance")
    async def balance_slash(self, interaction: discord.Interaction):
        coins, _ = self.bot.economy.balance(interaction.user.id)
        await interaction.response.send_message(f"🪙 **{coins}** coins")

    # --- shop ---
    def _shop_embed(self, user):
        owned = set(self.bot.economy.owned_titles(user.id))
        equipped = self.bot.economy.equipped_title(user.id)
        lines = []
        for item_id, (name, price) in TITLES.items():
            if item_id == equipped:
                tag = "✅ equipped"
            elif item_id in owned:
                tag = "owned"
            else:
                tag = f"{price} 🪙"
            lines.append(f"`{item_id}` — **{name}** · {tag}")
        return discord.Embed(
            title="🛍️ Title Shop",
            description="\n".join(lines) + "\n\nBuy with `;buy <id>`. Your title shows on your profile.",
            color=discord.Color.gold(),
        )

    def _buy(self, user, item):
        result = self.bot.economy.buy_title(user.id, str(user), item)
        if result == "unknown":
            return "No such item. See `;shop`."
        name = TITLES[item][0]
        return {
            "bought": f"🛍️ Purchased and equipped **{name}**!",
            "equipped": f"✅ Equipped **{name}** (you already owned it).",
            "poor": f"You can't afford **{name}** yet. Play more games or `;daily`.",
        }[result]

    @commands.command()
    async def shop(self, ctx):
        await ctx.send(embed=self._shop_embed(ctx.author))

    @app_commands.command(name="shop", description="Browse cosmetic titles you can buy")
    async def shop_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._shop_embed(interaction.user))

    @commands.command()
    async def buy(self, ctx, item: str):
        await ctx.send(self._buy(ctx.author, item.lower()))

    @app_commands.command(name="buy", description="Buy a cosmetic title")
    async def buy_slash(self, interaction: discord.Interaction, item: TitleId):
        await interaction.response.send_message(self._buy(interaction.user, item))

    # --- richest ---
    def _richest_embed(self):
        rows = self.bot.economy.top(10)
        if not rows:
            return discord.Embed(
                title="🪙 Richest players", description="No coins earned yet.", color=discord.Color.gold()
            )
        desc = "\n".join(f"{i}. {name}: {coins} 🪙" for i, (name, coins) in enumerate(rows, 1))
        return discord.Embed(title="🪙 Richest players", description=desc, color=discord.Color.gold())

    @commands.command(aliases=["rich", "baltop"])
    async def richest(self, ctx):
        await ctx.send(embed=self._richest_embed())

    @app_commands.command(name="richest", description="See the players with the most coins")
    async def richest_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._richest_embed())


async def setup(bot):
    await bot.add_cog(Economy(bot))
