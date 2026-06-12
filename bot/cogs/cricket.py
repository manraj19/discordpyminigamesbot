"""Cricket commands: a full match simulator, hand cricket, and live scores."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands
from tabulate import tabulate

from bot.core import config
from bot.data import CRICKET_NAMES
from bot.games.cricket import get_top_performers, simulate_innings

OVERS_TO_MAX_BOWLER = {5: 1, 10: 2, 20: 4}
HAND_CRICKET_OPTIONS = [1, 2, 3, 4, 6]


class Cricket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- shared chat helpers (channel/author based, so prefix and slash share them) ---
    async def _prompt(self, channel, author, text, *, valid=None, timeout=60.0):
        await channel.send(text)

        def check(m):
            if m.author != author or m.channel != channel:
                return False
            return valid(m.content) if valid else True

        try:
            return await self.bot.wait_for("message", check=check, timeout=timeout)
        except asyncio.TimeoutError:
            await channel.send("You took too long to respond. The simulation has been cancelled.")
            return None

    async def _send_highlights(self, channel, header, highlights):
        await channel.send(header)
        chunk = ""
        for line in highlights:
            if len(chunk) + len(line) + 1 > 1900:
                await channel.send(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            await channel.send(chunk)

    @staticmethod
    def _available_names(exclude=()):
        return [name for name in CRICKET_NAMES if name not in exclude]

    # --- simulate ---
    async def _simulate(self, channel, author):
        team1_name = await self._prompt(channel, author, "Enter the name of Team 1:")
        if team1_name is None:
            return
        team1_players = await self._prompt(
            channel,
            author,
            f"Enter the names of the players for {team1_name.content} (comma-separated) or type 'fill' to auto-fill:",
        )
        if team1_players is None:
            return
        if team1_players.content.lower() == "fill":
            available = self._available_names()
            if len(available) < 11:
                await channel.send("Not enough members in the predefined list to auto-fill Team 1.")
                return
            team1 = random.sample(available, 11)
        else:
            team1 = team1_players.content.split(",")

        team2_name = await self._prompt(channel, author, "Enter the name of Team 2:")
        if team2_name is None:
            return
        team2_players = await self._prompt(
            channel,
            author,
            f"Enter the names of the players for {team2_name.content} (comma-separated) or type 'fill' to auto-fill:",
        )
        if team2_players is None:
            return
        if team2_players.content.lower() == "fill":
            available = self._available_names(exclude=team1)
            if len(available) < 11:
                await channel.send("Not enough members in the predefined list to auto-fill Team 2.")
                return
            team2 = random.sample(available, 11)
        else:
            team2 = team2_players.content.split(",")

        overs_message = await self._prompt(
            channel,
            author,
            "Select the number of overs per innings (5, 10, 20):",
            valid=lambda c: c in ["5", "10", "20"],
        )
        if overs_message is None:
            return
        overs = int(overs_message.content)
        max_overs_per_bowler = OVERS_TO_MAX_BOWLER[overs]

        toss_winner = random.choice([team1_name.content, team2_name.content])
        await channel.send(f"{toss_winner} won the toss and chose to bat first.")

        if toss_winner == team1_name.content:
            batting_team, bowling_team = team1, team2
            batting_team_name, bowling_team_name = team1_name.content, team2_name.content
        else:
            batting_team, bowling_team = team2, team1
            batting_team_name, bowling_team_name = team2_name.content, team1_name.content

        runs1, wickets1, scores1, wickets_taken1, highlights1, _, overs1, balls_faced1 = simulate_innings(
            batting_team, bowling_team, overs, max_overs_per_bowler
        )
        await self._send_highlights(channel, "\nFirst Innings Highlights:", highlights1)

        top_batsmen1, top_bowlers1 = get_top_performers(scores1, wickets_taken1, balls_faced1)
        top_batsmen1_table = tabulate(
            top_batsmen1, headers=["Player", "Runs", "Balls Faced", "Strike Rate"], tablefmt="grid"
        )
        top_bowlers1_table = tabulate(top_bowlers1, headers=["Player", "Wickets"], tablefmt="grid")

        first_innings_embed = discord.Embed(title="First Innings Summary", color=0x00FF00)
        first_innings_embed.add_field(
            name=f"Top Batsmen from {batting_team_name}", value=f"```\n{top_batsmen1_table}\n```", inline=False
        )
        first_innings_embed.add_field(
            name=f"Top Bowlers from {bowling_team_name}", value=f"```\n{top_bowlers1_table}\n```", inline=False
        )
        first_innings_embed.add_field(
            name="Score",
            value=f"{batting_team_name}: {runs1} runs for {wickets1} wickets in {overs1} overs",
            inline=False,
        )
        await channel.send(embed=first_innings_embed)

        await asyncio.sleep(10)

        runs2, wickets2, scores2, wickets_taken2, highlights2, _chased, overs2, balls_faced2 = simulate_innings(
            bowling_team, batting_team, overs, max_overs_per_bowler, target=runs1
        )
        await self._send_highlights(channel, "\nSecond Innings Highlights:", highlights2)

        if runs2 > runs1:
            result = f"\n{bowling_team_name} wins by {10 - wickets2} wickets!"
        elif runs1 > runs2:
            result = f"\n{batting_team_name} wins by {runs1 - runs2} runs!"
        else:
            result = "\nThe match is a tie!"

        top_batsmen2, top_bowlers2 = get_top_performers(scores2, wickets_taken2, balls_faced2)
        top_batsmen2_table = tabulate(
            top_batsmen2, headers=["Player", "Runs", "Balls Faced", "Strike Rate"], tablefmt="grid"
        )
        top_bowlers2_table = tabulate(top_bowlers2, headers=["Player", "Wickets"], tablefmt="grid")

        final_scores = [
            [batting_team_name, runs1, wickets1, overs1],
            [bowling_team_name, runs2, wickets2, overs2],
        ]
        final_scores_table = tabulate(final_scores, headers=["Team", "Runs", "Wickets", "Overs"], tablefmt="grid")

        embed = discord.Embed(title="Cricket Match Simulation", color=0x00FF00)
        embed.add_field(name="Result", value=result, inline=False)
        embed.add_field(name="Top Batsmen in innings 1", value=f"```\n{top_batsmen1_table}\n```", inline=False)
        embed.add_field(name="Top Bowlers in innings 1", value=f"```\n{top_bowlers1_table}\n```", inline=False)
        embed.add_field(name="Top Batsmen in innings 2", value=f"```\n{top_batsmen2_table}\n```", inline=False)
        embed.add_field(name="Top Bowlers in innings 2", value=f"```\n{top_bowlers2_table}\n```", inline=False)
        embed.add_field(name="Final Scores", value=f"```\n{final_scores_table}\n```", inline=False)
        await channel.send(embed=embed)

    @commands.command(aliases=["sim"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def simulate(self, ctx):
        await self._simulate(ctx.channel, ctx.author)

    @app_commands.command(name="simulate", description="Simulate a full cricket match")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def simulate_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏏 Starting a cricket simulation! Follow the prompts below.")
        await self._simulate(interaction.channel, interaction.user)

    # --- hand cricket ---
    async def _hand_cricket(self, channel, author):
        user_score = 0
        bot_score = 0

        def check(m):
            return (
                m.author == author
                and m.channel == channel
                and m.content.isdigit()
                and int(m.content) in HAND_CRICKET_OPTIONS
            )

        await channel.send("First Half: You are batting. Type a number (1, 2, 3, 4, 6) to play your shot.")
        while True:
            try:
                message = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await channel.send("You took too long to respond. Game over.")
                return
            user_choice = int(message.content)
            bot_choice = random.choice(HAND_CRICKET_OPTIONS)
            await channel.send(f"You chose {user_choice}, Bot chose {bot_choice}")
            if user_choice == bot_choice:
                await channel.send(f"Out! Your score: {user_score}")
                break
            user_score += user_choice

        await channel.send("Second Half: Bot is batting. Type a number (1, 2, 3, 4, 6) to bowl.")
        while bot_score <= user_score:
            try:
                message = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await channel.send("You took too long to respond. Game over.")
                return
            user_choice = int(message.content)
            bot_choice = random.choice(HAND_CRICKET_OPTIONS)
            await channel.send(f"You chose {user_choice}, Bot chose {bot_choice}")
            if user_choice == bot_choice:
                await channel.send(f"Out! Bot's score: {bot_score}")
                break
            bot_score += bot_choice

        if bot_score > user_score:
            await channel.send(f"Bot wins!\n**Final scores**\nYou: {user_score}\nBot: {bot_score}")
        else:
            await channel.send(f"You win!\n**Final scores**\nYou: {user_score}\nBot: {bot_score}")

    @commands.command(aliases=["play"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def playcricket(self, ctx):
        await self._hand_cricket(ctx.channel, ctx.author)

    @app_commands.command(name="playcricket", description="Play a game of classic hand cricket")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def playcricket_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏏 Hand cricket — you're batting first!")
        await self._hand_cricket(interaction.channel, interaction.user)

    # --- live scores ---
    async def _live_result(self):
        url = f"https://api.cricapi.com/v1/currentMatches?apikey={config.CRICAPI_KEY}&offset=0"
        status, data = await self.bot.http_client.fetch_json(url)
        if status != 200 or not data:
            return "Could not fetch live cricket scores. Please try again later.", None
        matches = data.get("data", [])
        if not matches:
            return "No live matches found.", None

        embed = discord.Embed(title="Live Cricket Scores", color=0x11806A)
        for match in matches:
            if match.get("matchStarted") and not match.get("matchEnded"):
                team1, team2 = match["teams"][0], match["teams"][1]
                score = "\n".join(f"{s['inning']}: {s['r']}/{s['w']} in {s['o']} overs" for s in match.get("score", []))
                status_text = match.get("status", "Status not available")
                embed.add_field(
                    name=f"{team1} vs {team2}", value=f"Score:\n{score}\nStatus: {status_text}", inline=False
                )
        return None, embed

    @commands.command(aliases=["lc", "live"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def livecricket(self, ctx):
        error, embed = await self._live_result()
        await ctx.send(error) if error else await ctx.send(embed=embed)

    @app_commands.command(name="livecricket", description="Get live cricket scores")
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def livecricket_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        error, embed = await self._live_result()
        await (interaction.followup.send(error) if error else interaction.followup.send(embed=embed))


async def setup(bot):
    await bot.add_cog(Cricket(bot))
