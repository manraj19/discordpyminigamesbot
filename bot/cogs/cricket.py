"""Cricket commands: a full match simulator, hand cricket, and live scores."""

import asyncio
import random

import discord
from discord import app_commands
from discord.ext import commands
from tabulate import tabulate

from bot.core import emojis
from bot.data import CRICKET_BATSMEN, CRICKET_BOWLERS
from bot.games.cricket import get_top_performers, simulate_innings

HAND_CRICKET_OPTIONS = [1, 2, 3, 4, 6]
PACE_NORMAL = 1.4  # seconds between ordinary deliveries in the live replay
PACE_BIG = 2.2  # seconds to linger on wickets and milestones


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

    async def _replay(self, channel, team_name, innings_no, events, target=None):
        """Replay an innings as a single, live-updating scoreboard so it feels
        like watching the match unfold rather than reading a wall of text."""
        embed = discord.Embed(title=f"🏏 {team_name}: innings {innings_no}", color=0x1F8B4C)
        embed.description = "The players are walking out. 🏟️"
        message = await channel.send(embed=embed)

        feed = []
        for ev in events:
            header = f"## {ev['runs']}/{ev['wickets']}\n`{ev['overs']} overs`"
            if target is not None:
                need = target + 1 - ev["runs"]
                if need > 0:
                    header += f"  ·  🎯 need **{need}** to win"
            feed.append(ev["text"])
            feed = feed[-5:]
            embed.description = header + "\n\n" + "\n".join(feed)
            embed.color = 0xE74C3C if ev["kind"] == "wicket" else 0xF1C40F if ev["kind"] == "milestone" else 0x1F8B4C
            try:
                await message.edit(embed=embed)
            except discord.HTTPException:
                pass
            await asyncio.sleep(PACE_BIG if ev["kind"] in ("wicket", "milestone") else PACE_NORMAL)
        return message

    @staticmethod
    def _fill_team(exclude=()):
        """Build a balanced XI: 6 specialist batsmen up top, 5 bowlers at the tail."""
        bats = [n for n in CRICKET_BATSMEN if n not in exclude]
        bowls = [n for n in CRICKET_BOWLERS if n not in exclude]
        if len(bats) < 6 or len(bowls) < 5:
            return None
        return random.sample(bats, 6) + random.sample(bowls, 5)

    # --- simulate ---
    async def _team_prompt(self, channel, author, team_name, exclude=()):
        """Prompt for an XI (or 'fill'). Returns the player list, or None."""
        msg = await self._prompt(
            channel,
            author,
            f"Enter the 11 players for **{team_name}**, comma-separated, with your best "
            "batsmen first and bowlers last. Or type `fill` to auto-pick a balanced team:",
        )
        if msg is None:
            return None
        if msg.content.lower().strip() == "fill":
            team = self._fill_team(exclude=exclude)
            if team is None:
                await channel.send("Not enough players left in the roster to auto-fill. Please enter names manually.")
            return team
        return [p.strip() for p in msg.content.split(",")]

    async def _simulate(self, channel, author):
        if not self.bot.begin_session(author.id):
            await channel.send("⚠️ Finish your current game first.")
            return
        try:
            await self._run_simulate(channel, author)
        finally:
            self.bot.end_session(author.id)

    async def _run_simulate(self, channel, author):
        team1_name = await self._prompt(channel, author, "Enter the name of Team 1:")
        if team1_name is None:
            return
        team1 = await self._team_prompt(channel, author, team1_name.content)
        if team1 is None:
            return

        team2_name = await self._prompt(channel, author, "Enter the name of Team 2:")
        if team2_name is None:
            return
        team2 = await self._team_prompt(channel, author, team2_name.content, exclude=team1)
        if team2 is None:
            return

        overs_message = await self._prompt(
            channel,
            author,
            "Select the number of overs per innings (5, 10, 20):",
            valid=lambda c: c in ["5", "10", "20"],
        )
        if overs_message is None:
            return
        overs = int(overs_message.content)
        max_overs_per_bowler = overs // 5  # each bowler is capped at a fifth of the innings

        toss_winner = random.choice([team1_name.content, team2_name.content])
        await channel.send(f"{emojis.COIN} **{toss_winner}** won the toss and chose to bat first!")
        await asyncio.sleep(1.5)

        if toss_winner == team1_name.content:
            batting_team, bowling_team = team1, team2
            bat_name, bowl_name = team1_name.content, team2_name.content
        else:
            batting_team, bowling_team = team2, team1
            bat_name, bowl_name = team2_name.content, team1_name.content

        # --- First innings (played out live) ---
        runs1, wickets1, scores1, wkts1, events1, _c1, overs1, balls1, _bo1 = simulate_innings(
            batting_team, bowling_team, overs, max_overs_per_bowler
        )
        await self._replay(channel, bat_name, 1, events1)
        await channel.send(
            f"🏁 Innings over. **{bat_name}: {runs1}/{wickets1}** ({overs1} ov). Target: **{runs1 + 1}**."
        )
        await asyncio.sleep(3)
        await channel.send("*Innings break.*")
        await asyncio.sleep(2)

        # --- Second innings (the chase, played out live) ---
        runs2, wickets2, scores2, wkts2, events2, _chased, overs2, balls2, _bo2 = simulate_innings(
            bowling_team, batting_team, overs, max_overs_per_bowler, target=runs1
        )
        await self._replay(channel, bowl_name, 2, events2, target=runs1)

        if runs2 > runs1:
            result = f"{emojis.TROPHY} **{bowl_name}** win by {10 - wickets2} wickets!"
        elif runs1 > runs2:
            result = f"{emojis.TROPHY} **{bat_name}** win by {runs1 - runs2} runs!"
        else:
            result = "🤝 The match is a tie!"
        await channel.send(result)
        await asyncio.sleep(1)

        # --- Scorecard summary ---
        tb1, bw1 = get_top_performers(scores1, wkts1, balls1)
        tb2, bw2 = get_top_performers(scores2, wkts2, balls2)
        bat_headers = ["Player", "Runs", "Balls", "SR"]
        bowl_headers = ["Player", "Wickets"]
        embed = discord.Embed(title="📊 Match Summary", color=0x1F8B4C)
        embed.add_field(name="Result", value=result, inline=False)
        embed.add_field(
            name=f"{bat_name}: {runs1}/{wickets1} ({overs1} ov)",
            value=f"```\n{tabulate(tb1, headers=bat_headers, tablefmt='grid')}\n```",
            inline=False,
        )
        embed.add_field(
            name=f"Top bowlers ({bowl_name})",
            value=f"```\n{tabulate(bw1, headers=bowl_headers, tablefmt='grid')}\n```",
            inline=False,
        )
        embed.add_field(
            name=f"{bowl_name}: {runs2}/{wickets2} ({overs2} ov)",
            value=f"```\n{tabulate(tb2, headers=bat_headers, tablefmt='grid')}\n```",
            inline=False,
        )
        embed.add_field(
            name=f"Top bowlers ({bat_name})",
            value=f"```\n{tabulate(bw2, headers=bowl_headers, tablefmt='grid')}\n```",
            inline=False,
        )
        await channel.send(embed=embed)

    @commands.command(aliases=["sim"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def simulate(self, ctx):
        await self._simulate(ctx.channel, ctx.author)

    @app_commands.command(name="simulate", description="Simulate a full cricket match")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def simulate_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"{emojis.BATBALL} Starting a cricket simulation! Follow the prompts below."
        )
        await self._simulate(interaction.channel, interaction.user)

    # --- hand cricket ---
    async def _hand_cricket(self, channel, author):
        if not self.bot.begin_session(author.id):
            await channel.send("⚠️ Finish your current game first.")
            return
        try:
            await self._run_hand_cricket(channel, author)
        finally:
            self.bot.end_session(author.id)

    async def _run_hand_cricket(self, channel, author):
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
            coins = self.bot.reward(author, 1, "playcricket")
            await channel.send(
                f"You win!\n**Final scores**\nYou: {user_score}\nBot: {bot_score}\n{emojis.COIN} **+{coins}** MiniCoins"
            )

    @commands.command(aliases=["play"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def playcricket(self, ctx):
        await self._hand_cricket(ctx.channel, ctx.author)

    @app_commands.command(name="playcricket", description="Play a game of classic hand cricket")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.user.id)
    async def playcricket_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{emojis.BATBALL} Hand cricket! You're batting first.")
        await self._hand_cricket(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(Cricket(bot))
