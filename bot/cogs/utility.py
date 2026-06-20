"""Utility commands: dictionary lookups, profiles, leaderboards, bot info."""

import datetime
from typing import Literal
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import config, embeds
from bot.services.economy import TITLES
from bot.services.scores import SUPPORTED_GAMES


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- dictionary ---
    async def _define(self, word):
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word)}"
        status, data = await self.bot.http_client.fetch_json(url)
        if status != 200 or not data or isinstance(data, dict):
            return f"No definition found for '{word}'.", None

        embed = discord.Embed(title=f"Definition of {word}", color=0x7289DA)
        for meaning in data[0]["meanings"]:
            definitions_text = "\n".join(d["definition"] for d in meaning["definitions"])
            if len(definitions_text) > 1024:
                definitions_text = definitions_text[:1021] + "..."
            embed.add_field(name=meaning["partOfSpeech"], value=definitions_text, inline=False)
        embed.set_footer(text="🤓")
        return None, embed

    @commands.command(aliases=["def"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def define(self, ctx, *, word: str):
        error, embed = await self._define(word)
        await (ctx.send(error) if error else ctx.send(embed=embed))

    @app_commands.command(name="define", description="Define a word")
    @app_commands.describe(word="The word to define")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def define_slash(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer()
        error, embed = await self._define(word)
        await (interaction.followup.send(error) if error else interaction.followup.send(embed=embed))

    # --- urban dictionary ---
    async def _urban(self, term):
        url = f"https://api.urbandictionary.com/v0/define?term={quote(term)}"
        status, data = await self.bot.http_client.fetch_json(url)
        if status != 200 or not data or not data.get("list"):
            return f"No definition found for '{term}'.", None

        embed = discord.Embed(title=f"Urban Dictionary: {term}", color=0x7289DA)
        for i, definition in enumerate(data["list"][:5], 1):
            def_text = definition["definition"]
            example_text = definition["example"]
            if len(def_text) > 1024:
                def_text = def_text[:1021] + "..."
            if len(example_text) > 1024:
                example_text = example_text[:1021] + "..."
            embed.add_field(name=f"Definition {i}", value=def_text, inline=False)
            embed.add_field(name="Example", value=example_text, inline=False)
        embed.set_footer(text="If this shows something offensive, it's not my fault. Blame Urban Dictionary.")
        return None, embed

    @commands.command(aliases=["urban"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def urbandictionary(self, ctx, *, term: str):
        error, embed = await self._urban(term)
        await (ctx.send(error) if error else ctx.send(embed=embed))

    @app_commands.command(name="urbandictionary", description="Get a word's definition from Urban Dictionary")
    @app_commands.describe(term="The term to look up")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def urban_slash(self, interaction: discord.Interaction, term: str):
        await interaction.response.defer()
        error, embed = await self._urban(term)
        await (interaction.followup.send(error) if error else interaction.followup.send(embed=embed))

    # --- leaderboard ---
    def _leaderboard(self, game):
        game = game.lower()
        if game not in SUPPORTED_GAMES:
            return "Supported leaderboards: " + ", ".join(SUPPORTED_GAMES) + ".", None
        rows = self.bot.scores.top(game, 10)
        if not rows:
            return f"No scores available yet for {game}.", None
        description = "\n".join(f"{i}. {username}: {score}" for i, (username, score) in enumerate(rows, 1))
        return None, embeds.branded(title=f"{game.capitalize()} Leaderboard", description=description)

    @commands.command(aliases=["lb"])
    async def leaderboard(self, ctx, game: str):
        error, embed = self._leaderboard(game)
        await (ctx.send(error) if error else ctx.send(embed=embed))

    @app_commands.command(name="leaderboard", description="View a game's leaderboard")
    @app_commands.describe(game="Which game's leaderboard to view")
    async def leaderboard_slash(
        self,
        interaction: discord.Interaction,
        game: Literal[
            "dino",
            "flagle",
            "fight",
            "connect4",
            "rockpaperscissors",
            "tictactoe",
            "wordguess",
            "emojiguess",
            "mathematics",
            "unscramble",
        ],
    ):
        error, embed = self._leaderboard(game)
        await (interaction.response.send_message(error) if error else interaction.response.send_message(embed=embed))

    # --- profile ---
    def _profile(self, user):
        embed = embeds.branded(title=f"{user}'s Game Profile")
        title_id = self.bot.economy.equipped_title(user.id)
        if title_id:
            embed.description = f"*{TITLES[title_id][0]}*"
        embed.set_thumbnail(url=user.display_avatar.url)
        for game in SUPPORTED_GAMES:
            score = self.bot.scores.user_score(user.id, game)
            if score is None:
                value = "Score: N/A\nRank: N/A"
            else:
                value = f"Score: {score}\nRank: {self.bot.scores.rank(game, score)}"
            embed.add_field(name=game.capitalize(), value=value, inline=True)
        coins, streak = self.bot.economy.balance(user.id)
        embed.add_field(name="🪙 Coins", value=f"{coins}\n🔥 {streak}-day streak", inline=True)
        return embed

    @commands.command()
    async def profile(self, ctx):
        await ctx.send(embed=self._profile(ctx.author))

    @app_commands.command(name="profile", description="View your game profile")
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
        embed.add_field(name="Bot Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Invite Link", value=f"[Invite the Bot]({config.INVITE_URL})", inline=False)
        embed.add_field(name="Support Server", value=f"[Join Support Server]({config.SUPPORT_SERVER})", inline=False)
        embed.add_field(name="Top.gg Page", value=f"[Vote for the Bot]({config.TOPGG_VOTE})", inline=False)
        embed.set_footer(text=f"Uptime: {uptime_str}")
        return embed

    @commands.command(aliases=["info", "bot"])
    async def botinfo(self, ctx):
        await ctx.send(embed=self._botinfo_embed())

    @app_commands.command(name="botinfo", description="Get information about the bot")
    async def botinfo_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._botinfo_embed())


async def setup(bot):
    await bot.add_cog(Utility(bot))
