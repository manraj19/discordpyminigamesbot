"""Bomb Party: 2 to 6 players pass a lit bomb, typing words that contain the
shown letters. Rules live in bot.games.bombparty; this owns the clock and the
messages.

Each turn starts a fresh clock (see ``turn_seconds``), so nobody can stall and
hand over a bomb that is about to go off. The countdown is a Discord relative
timestamp, which the client ticks down on its own, so a long game costs one edit
per turn.
"""

import asyncio
import contextlib
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import emojis
from bot.core.rewards import RewardResult
from bot.games.bombparty import (
    MIN_PLAYERS,
    accept,
    advance,
    current_player,
    explode,
    judge,
    new_game,
    normalize,
    sample_prompt,
    turn_seconds,
    winner,
)
from bot.views.bombparty import LobbyView

GAME = "bombparty"

# Why a guess bounced. The clock keeps running either way, which is the point.
VERDICT_REACTION = {"no_prompt": "❌", "not_a_word": "❓", "used": "♻️"}


class BombParty(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = set()  # games are short lived, so memory is enough

    async def _play(self, channel, host):
        if channel.id in self.active_channels:
            await channel.send("There's already a bomb party going in this channel.")
            return
        self.active_channels.add(channel.id)
        joined = []
        try:
            if not self.bot.begin_session(host.id):
                await channel.send("⚠️ Finish your current game first.")
                return
            joined.append(host)
            view = LobbyView(host, joined, self.bot)
            view.message = await channel.send(embed=view.embed(), view=view)
            await view.wait()
            if len(joined) < MIN_PLAYERS:
                await channel.send("Nobody else joined, so the bomb party is off.")
                return
            await self._run(channel, list(joined))
        finally:
            # Whatever happened, free the channel and everyone's game slot.
            self.active_channels.discard(channel.id)
            for member in joined:
                self.bot.end_session(member.id)

    async def _run(self, channel, players):
        rng = random.Random()
        game = new_game([player.id for player in players])
        by_id = {player.id: player for player in players}
        game.prompt = sample_prompt(rng, game.round)
        deadline = time.time() + turn_seconds(game.round)
        board = await channel.send(embed=self._board(game, by_id, deadline))

        while True:
            holder = by_id[current_player(game)]
            word = await self._await_word(channel, holder, game, deadline)
            if word is None:
                knocked_out = explode(game)
                if knocked_out:
                    await channel.send(f"💥 The bomb goes off. {holder.mention} is out!")
                else:
                    left = game.lives[holder.id]
                    await channel.send(f"💥 Boom. {holder.mention} loses a life, **{left}** to go.")
            elif accept(game, word):
                await channel.send(f"🔤 {holder.mention} used the whole alphabet and takes a life back!")
            if winner(game) is not None:
                break
            advance(game)
            game.prompt = sample_prompt(rng, game.round)
            deadline = time.time() + turn_seconds(game.round)  # every turn starts clean
            with contextlib.suppress(discord.HTTPException):
                await board.edit(embed=self._board(game, by_id, deadline))

        with contextlib.suppress(discord.HTTPException):
            await board.edit(embed=self._final_board(game, by_id))  # no stale countdown left behind
        await self._finish(channel, game, by_id)

    async def _await_word(self, channel, player, game, deadline):
        """Wait for the holder to type something valid. Returns the word, or None
        if the fuse ran out. Wrong guesses cost time, not a fresh timer."""

        def check(message):
            return message.channel == channel and message.author.id == player.id

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            try:
                message = await self.bot.wait_for("message", check=check, timeout=remaining)
            except asyncio.TimeoutError:
                return None
            word = normalize(message.content)
            verdict = judge(game, word)
            if verdict == "ok":
                return word
            with contextlib.suppress(discord.HTTPException):
                await message.add_reaction(VERDICT_REACTION[verdict])

    def _board(self, game, by_id, deadline):
        rows = []
        for pid in game.players:
            lives = game.lives[pid]
            hearts = emojis.HEALTH * lives if lives else "💀"
            marker = "➡️ " if pid == current_player(game) else ""
            rows.append(f"{marker}{by_id[pid].display_name}  {hearts}")
        holder = by_id[current_player(game)]
        embed = discord.Embed(
            title="💣 Bomb Party",
            description=(
                f"# {game.prompt.upper()}\n"
                f"{holder.mention}, type a word with those letters in it.\n"
                f"🧨 It blows <t:{int(deadline)}:R>"
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(name="Players", value="\n".join(rows))
        embed.set_footer(text=f"Round {game.round} · wrong guesses don't buy you more time")
        return embed

    def _final_board(self, game, by_id):
        """Replaces the live board once someone has won, so the message does not
        sit there with a dead countdown and a prompt nobody has to answer."""
        champion = by_id[winner(game)]
        embed = discord.Embed(
            title="💣 Bomb Party",
            description=f"{emojis.TROPHY} **{champion.display_name}** made it out. Game over.",
            color=discord.Color.gold(),
        )
        rows = [
            f"{by_id[pid].display_name}  {emojis.HEALTH * game.lives[pid] if game.lives[pid] else '💀'}"
            for pid in game.players
        ]
        embed.add_field(name="Final standings", value="\n".join(rows))
        embed.set_footer(text=f"Lasted {game.round} rounds · {len(game.used)} words played")
        return embed

    async def _finish(self, channel, game, by_id):
        champion = by_id[winner(game)]
        result = self.bot.reward(champion, 1, GAME)
        lines = [f"{emojis.TROPHY} {champion.mention} is the last one standing!"]
        if result.line():
            lines.append(result.line())
        for pid in game.players:
            if pid == champion.id:
                continue
            member = by_id[pid]
            quests, level_up, bonus = self.bot.quest_event(pid, str(member), "game_play", 1)
            played = RewardResult(coins=bonus, level_up=level_up, quests=quests).line()
            if played:
                lines.append(f"{member.display_name}: {played}")
        await channel.send("\n".join(lines))

    @commands.command(aliases=["bomb", "bp"])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    async def bombparty(self, ctx):
        await self._play(ctx.channel, ctx.author)

    @app_commands.command(name="bombparty", description="Start a word game for 2 to 6 players")
    @app_commands.checks.cooldown(1, 30, key=lambda i: i.channel_id)
    async def bombparty_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("💣 Opening a bomb party!")
        await self._play(interaction.channel, interaction.user)


async def setup(bot):
    await bot.add_cog(BombParty(bot))
