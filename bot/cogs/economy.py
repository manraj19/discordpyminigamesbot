"""Economy: a daily coin claim with a streak, a balance check, and a small
cosmetic-title shop that coins are spent on."""

import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import config, emojis
from bot.games.achievements import ACHIEVEMENTS
from bot.services.economy import TITLES

log = logging.getLogger(__name__)

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
                description=f"Come back tomorrow! {emojis.STREAK} **{streak}**-day streak · balance **{coins}** MiniCoins.",
                color=discord.Color.orange(),
            )
        return discord.Embed(
            title="🪙 Daily reward claimed!",
            description=f"{emojis.COIN} +**{reward}** MiniCoins · {emojis.STREAK} **{streak}**-day streak · balance **{coins}** MiniCoins.",
            color=discord.Color.gold(),
        )

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def daily(self, ctx):
        await ctx.send(embed=self._claim(ctx.author))

    @app_commands.command(name="daily", description="Claim your daily MiniCoins and keep your streak alive")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def daily_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._claim(interaction.user))

    # --- balance ---
    @commands.command(aliases=["bal", "coins"])
    async def balance(self, ctx):
        coins, _ = self.bot.economy.balance(ctx.author.id)
        await ctx.send(f"{emojis.COIN} **{coins}** MiniCoins")

    @app_commands.command(name="balance", description="Check your MiniCoins balance")
    async def balance_slash(self, interaction: discord.Interaction):
        coins, _ = self.bot.economy.balance(interaction.user.id)
        await interaction.response.send_message(f"{emojis.COIN} **{coins}** MiniCoins")

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
                tag = f"{price} {emojis.COIN}"
            lines.append(f"`{item_id}` **{name}** · {tag}")
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
                title="🪙 Richest players", description="No MiniCoins earned yet.", color=discord.Color.gold()
            )
        desc = "\n".join(f"{i}. {name}: {coins} {emojis.COIN}" for i, (name, coins) in enumerate(rows, 1))
        return discord.Embed(title="🪙 Richest players", description=desc, color=discord.Color.gold())

    @commands.command(aliases=["rich", "baltop"])
    async def richest(self, ctx):
        await ctx.send(embed=self._richest_embed())

    @app_commands.command(name="richest", description="See the players with the most MiniCoins")
    async def richest_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._richest_embed())

    # --- achievements ---
    def _achievements_embed(self, member):
        self.bot.award_achievements(member.id, str(member))
        earned = set(self.bot.economy.earned_achievements(member.id))
        lines = [
            f"{'✅' if aid in earned else '🔒'} **{name}**: {desc}"
            for aid, (name, desc, _check) in ACHIEVEMENTS.items()
        ]
        return discord.Embed(
            title=f"🏅 Achievements ({len(earned)}/{len(ACHIEVEMENTS)})",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )

    @commands.command(aliases=["achs"])
    async def achievements(self, ctx, member: discord.Member = None):
        await ctx.send(embed=self._achievements_embed(member or ctx.author))

    @app_commands.command(name="achievements", description="View earned achievements")
    @app_commands.describe(member="Whose achievements to view (defaults to you)")
    async def achievements_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.send_message(embed=self._achievements_embed(member or interaction.user))

    # --- Top.gg vote rewards ---
    async def _vote(self, user):
        # Call the Top.gg check endpoint directly. topggpy's get_user_vote only
        # parses the JSON body when Content-Type is exactly
        # "application/json; charset=utf-8" and crashes on the live API's
        # response otherwise, so we fetch and parse it ourselves.
        link = config.TOPGG_VOTE
        if not config.TOPGG_TOKEN:
            return f"Vote for the bot here: {link}"
        status, data = await self.bot.http_client.fetch_json(
            f"https://top.gg/api/bots/{config.BOT_ID}/check",
            headers={"Authorization": config.TOPGG_TOKEN},
            params={"userId": str(user.id)},
        )
        if status != 200 or not isinstance(data, dict):
            log.warning("Top.gg vote check failed (status %s) for user %s", status, user.id)
            return f"Couldn't reach Top.gg right now. Vote here: {link}"
        if not data.get("voted"):
            return f"You haven't voted recently. Vote here, then run `;vote` again to claim: {link}"
        claimed, reward, hours = self.bot.economy.claim_vote(user.id, str(user))
        if claimed:
            return f"{emojis.COIN} Thanks for voting! **+{reward}** MiniCoins."
        return f"You already claimed this vote. Your next reward is available in about {hours}h."

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vote(self, ctx):
        await ctx.send(await self._vote(ctx.author))

    @app_commands.command(name="vote", description="Vote for the bot on Top.gg and claim a reward")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def vote_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(await self._vote(interaction.user))


async def setup(bot):
    await bot.add_cog(Economy(bot))
