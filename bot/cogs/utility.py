"""Utility commands: dictionary lookups, profiles, leaderboards, bot info."""

import datetime
import re
from typing import Literal
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import config, embeds, emojis
from bot.core.rewards import RewardResult, progress_bar
from bot.games.achievements import ACHIEVEMENTS
from bot.games.duel import XP_PER_LEVEL
from bot.services.economy import title_name
from bot.services.scores import SUPPORTED_GAMES, game_title, score_text
from bot.views.pages import PagedView

MAX_DEFINITIONS = 8  # on a page of ;define, so a word with dozens of senses stays readable


def _clip(text, limit=1024):
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _urban_text(text, limit):
    """Urban Dictionary text for an embed field, minus its [cross-link] brackets."""
    return _clip(re.sub(r"[\[\]]", "", text).strip(), limit)


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- dictionary ---
    async def _define(self, word):
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word, safe='')}"
        status, data = await self.bot.http_client.fetch_json(url)
        if status != 200 or not data or isinstance(data, dict) or not data[0]["meanings"]:
            return f"No definition found for '{word[:100]}'.", None

        pages = []
        for meaning in data[0]["meanings"]:
            part = meaning["partOfSpeech"]
            senses = (f"{i}. {d['definition']}" for i, d in enumerate(meaning["definitions"][:MAX_DEFINITIONS], 1))
            embed = discord.Embed(
                title=f"Definition of {word[:100]}",
                description=_clip(f"**{part}**\n" + "\n".join(senses), 4000),
                color=0x7289DA,
            )
            embed.set_footer(text="🤓")
            pages.append((part, embed))
        return None, pages

    @commands.command(aliases=["def"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def define(self, ctx, *, word: str):
        error, pages = await self._define(word)
        await (ctx.send(error) if error else PagedView(ctx.author.id, pages).send(ctx))

    @app_commands.command(name="define", description="Define a word")
    @app_commands.describe(word="The word to define")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def define_slash(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer()
        error, pages = await self._define(word)
        await (interaction.followup.send(error) if error else PagedView(interaction.user.id, pages).send(interaction))

    # --- urban dictionary ---
    async def _urban(self, term):
        url = f"https://api.urbandictionary.com/v0/define?term={quote(term)}"
        status, data = await self.bot.http_client.fetch_json(url)
        if status != 200 or not data or not data.get("list"):
            return f"No definition found for '{term[:100]}'.", None

        pages = []
        for i, definition in enumerate(data["list"][:5], 1):
            embed = discord.Embed(
                title=f"Urban Dictionary: {term[:100]}",
                description=_urban_text(definition["definition"], 2000) or "?",
                color=0x7289DA,
            )
            example = _urban_text(definition["example"], 1000)
            if example:
                embed.add_field(name="Example", value=example, inline=False)
            embed.set_footer(text="If this shows something offensive, it's not my fault. Blame Urban Dictionary.")
            pages.append((f"Definition {i}", embed))
        return None, pages

    @commands.command(aliases=["urban"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def urbandictionary(self, ctx, *, term: str):
        error, pages = await self._urban(term)
        await (ctx.send(error) if error else PagedView(ctx.author.id, pages).send(ctx))

    @app_commands.command(name="urbandictionary", description="Get a word's definition from Urban Dictionary")
    @app_commands.describe(term="The term to look up")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def urban_slash(self, interaction: discord.Interaction, term: str):
        await interaction.response.defer()
        error, pages = await self._urban(term)
        await (interaction.followup.send(error) if error else PagedView(interaction.user.id, pages).send(interaction))

    # --- leaderboard (global by default, opt-in per server) ---
    def _leaderboard(self, game, guild_id):
        game = game.lower()
        command = self.bot.get_command(game)  # aliases count, so ;lb c4 works like ;c4 does
        game = command.name if command else game
        if game not in SUPPORTED_GAMES:
            return "Supported leaderboards: " + ", ".join(SUPPORTED_GAMES) + ".", None
        rows = self.bot.scores.top(game, guild_id, 10)
        if not rows:
            where = " on this server" if guild_id else ""
            return f"No scores yet for {game_title(game)}{where}.", None
        description = "\n".join(
            f"{i}. {discord.utils.escape_markdown(username)}: {score_text(game, score)}"
            for i, (username, score) in enumerate(rows, 1)
        )
        embed = embeds.branded(title=f"{game_title(game)} Leaderboard", description=description)
        embed.set_footer(text="This server" if guild_id else "Global, all servers")
        return None, embed

    @commands.command(aliases=["lb"])
    async def leaderboard(self, ctx, game: str, scope: str = "global"):
        guild_id = ctx.guild.id if scope.lower() == "server" and ctx.guild else None
        error, embed = self._leaderboard(game, guild_id)
        await (ctx.send(error) if error else ctx.send(embed=embed))

    @app_commands.command(name="leaderboard", description="View a game's leaderboard (global, or this server)")
    @app_commands.describe(game="Which game's leaderboard to view", scope="Global (default) or this server")
    @app_commands.choices(game=[app_commands.Choice(name=game_title(g), value=g) for g in SUPPORTED_GAMES])
    async def leaderboard_slash(
        self, interaction: discord.Interaction, game: str, scope: Literal["global", "server"] = "global"
    ):
        guild_id = interaction.guild.id if scope == "server" and interaction.guild else None
        error, embed = self._leaderboard(game, guild_id)
        await (interaction.response.send_message(error) if error else interaction.response.send_message(embed=embed))

    # --- profile (overall, across all servers) ---
    def _profile(self, user):
        unlocked = RewardResult(new_achievements=self.bot.award_achievements(user.id, str(user))).line()
        embed = embeds.branded(title=f"{user}'s Game Profile")
        title_id = self.bot.economy.equipped_title(user.id)
        if title_id:
            embed.description = f"## 🏅 {title_name(title_id)}"
        embed.set_thumbnail(url=user.display_avatar.url)
        rec = self.bot.duel.get_or_create(user.id, str(user))
        into = rec["xp"] % XP_PER_LEVEL
        embed.add_field(
            name="⭐ Level",
            value=f"**{rec['level']}**\n{progress_bar(into, XP_PER_LEVEL)} {into}/{XP_PER_LEVEL} XP",
            inline=True,
        )
        coins, streak = self.bot.economy.balance(user.id)
        shield = f"\n{emojis.SHIELD} streak shield ready" if self.bot.economy.owns(user.id, "streakshield") else ""
        embed.add_field(name="🪙 MiniCoins", value=f"{coins}\n{emojis.STREAK} {streak}-day streak{shield}", inline=True)
        embed.add_field(
            name="⚔️ Duel", value=f"Rating **{rec['rating']}**\n{rec['wins']}W / {rec['losses']}L", inline=True
        )
        earned = len(self.bot.economy.earned_achievements(user.id))
        embed.add_field(name="🏅 Achievements", value=f"{earned}/{len(ACHIEVEMENTS)}", inline=True)
        scores = ((game, self.bot.scores.user_score(user.id, game)) for game in SUPPORTED_GAMES)
        played = [
            f"**{game_title(game)}**: {score_text(game, score)} · rank #{self.bot.scores.rank(game, score):,}"
            for game, score in scores
            if score is not None
        ]
        embed.add_field(
            name="🎮 Game scores", value="\n".join(played) or "Nothing yet. `;help` lists the games.", inline=False
        )
        if unlocked:
            embed.add_field(name="🎉 Just unlocked", value=unlocked, inline=False)
        embed.set_footer(text="Stats across all servers · gear and loadout in ;duelist")
        return embed

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def profile(self, ctx):
        await ctx.send(embed=self._profile(ctx.author))

    @app_commands.command(name="profile", description="View your game profile")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def profile_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._profile(interaction.user))

    # --- bot info ---
    def _botinfo_embed(self):
        uptime = datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time
        uptime_str = str(uptime).split(".")[0]
        embed = discord.Embed(title="Bot Information", color=discord.Color.dark_embed())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name="Servers and Shards",
            value=f"{len(self.bot.guilds)} Servers, {len(self.bot.shards)} Shards",
            inline=True,
        )
        embed.add_field(name="Bot Latency", value=f"{self.bot.latency * 1000:.0f}ms", inline=True)
        embed.add_field(name="Invite Link", value=f"[Invite the Bot]({config.INVITE_URL})", inline=False)
        embed.add_field(name="Support Server", value=f"[Join Support Server]({config.SUPPORT_SERVER})", inline=False)
        embed.add_field(name="Top.gg Page", value=f"[Vote for the Bot]({config.TOPGG_VOTE})", inline=False)
        embed.add_field(
            name="Support",
            value=f"[Buy me a coffee]({config.KOFI_URL}) if you feel like it. The bot stays free either way, "
            f"see `{config.COMMAND_PREFIX}donate`.",
            inline=False,
        )
        embed.set_footer(text=f"Uptime: {uptime_str}")
        return embed

    # --- donate ---
    def _donate_embed(self):
        prefix = config.COMMAND_PREFIX
        embed = embeds.branded(
            title="☕ Support MiniGames",
            description=(
                "MiniGames is free, and it stays that way. Every game, every command, and anything I add later: "
                "no paywalls, no premium tier, nothing locked behind money.\n\n"
                "If you've had fun with it and want to help cover the hosting, there's a Ko-fi below. It gets you "
                "a supporter role in the support server. That's the whole list. No bonus MiniCoins, no exclusive "
                "games, no edge over anyone else, because that would make the bot worse for everyone who doesn't pay."
            ),
        )
        embed.add_field(name="Ko-fi", value=f"[ko-fi.com/manraj1]({config.KOFI_URL})", inline=False)
        embed.add_field(
            name="Free ways to help",
            value=f"`{prefix}vote` every 12 hours, or [invite the bot]({config.INVITE_URL}) somewhere new. "
            "Telling a friend works too.",
            inline=False,
        )
        embed.set_footer(text="Skipping this costs you nothing. Playing is support too.")
        return embed

    @commands.command(aliases=["support", "kofi"])
    async def donate(self, ctx):
        await ctx.send(embed=self._donate_embed())

    @app_commands.command(name="donate", description="Support the bot (entirely optional, nothing gets unlocked)")
    async def donate_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._donate_embed())

    @commands.command(aliases=["info", "bot"])
    async def botinfo(self, ctx):
        await ctx.send(embed=self._botinfo_embed())

    @app_commands.command(name="botinfo", description="Get information about the bot")
    async def botinfo_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._botinfo_embed())


async def setup(bot):
    await bot.add_cog(Utility(bot))
