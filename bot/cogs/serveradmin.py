"""Server admin tools: pin games to channels, and turn the bot off in a channel.

``;setchannel connect4 #connect-four`` means Connect 4 can only be played in
#connect-four, and #connect-four only runs the games pinned to it.
``;disable #memes`` turns the bot off in #memes and its threads until
``;enable``. Both rules are enforced in bot.core.checks, before any command runs.

These are hybrid commands, so one handler serves both ``;setchannel`` and
``/setchannel``. The owner can run them anywhere, and ``;disable``/``;enable``
also take a channel ID from a DM.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.help import GAMES
from bot.core import config, embeds
from bot.core.checks import join_and, live_pins, mention_all
from bot.views.duel import add_lines_field


async def _game_autocomplete(interaction, current):
    return [app_commands.Choice(name=g, value=g) for g in sorted(GAMES) if current.lower() in g][:25]


def server_admin():
    """Members with the Administrator permission, plus the bot owner anywhere."""

    async def predicate(ctx):
        if ctx.author.id == config.OWNER_ID:
            return True
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        if not ctx.author.guild_permissions.administrator:
            raise commands.MissingPermissions(["administrator"])
        return True

    return commands.check(predicate)


def _here(ctx):
    """The channel a command was run in, as a thread's parent channel. None in DMs."""
    return (getattr(ctx.channel, "parent", None) or ctx.channel) if ctx.guild else None


class ServerAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _game(self, name):
        """A typed game name or alias as its command name, or None if it isn't a game."""
        command = self.bot.get_command(name.lower().lstrip(";/"))
        return command.qualified_name if command and command.qualified_name in GAMES else None

    # --- pinning games to channels ---
    @commands.hybrid_command(description="Pin a game to a channel (server admins only)")
    @app_commands.describe(game="The game to pin", channel="The channel it should be played in")
    @app_commands.autocomplete(game=_game_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @commands.guild_only()
    @server_admin()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def setchannel(self, ctx, game: str, channel: discord.TextChannel):
        name = self._game(game)
        if name is None:
            await ctx.send(f"There's no game called `{game[:40]}`. `;help` lists every game.")
            return
        lock = self.bot.channel_lock
        if channel.id in lock.game_channels(ctx.guild.id).get(name, ()):
            await ctx.send(f"`{name}` is already pinned to {channel.mention}.")
            return
        lock.pin_game(ctx.guild.id, name, channel.id)
        pins = live_pins(self.bot, ctx.guild.id)
        here = join_and(f"`{g}`" for g in sorted(g for g, chans in pins.items() if channel.id in chans))
        await ctx.send(
            f"📌 `{name}` can now only be played in {mention_all(pins[name])}, and {channel.mention} only "
            f"runs {here}. To undo it, run `;unsetchannel {name}` {channel.mention}."
        )

    @commands.hybrid_command(description="Unpin games from a channel (server admins only)")
    @app_commands.describe(
        game="The game to unpin. Leave it empty to clear the whole channel",
        channel="The channel to unpin from. Leave it empty to unpin the game everywhere",
    )
    @app_commands.autocomplete(game=_game_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @commands.guild_only()
    @server_admin()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def unsetchannel(self, ctx, game: str = None, channel: discord.TextChannel = None):
        name = self._game(game) if game else None
        if game and not name and channel is None:
            # ;unsetchannel #connect-four: the one argument is a channel, not a game.
            try:
                channel, game = await commands.TextChannelConverter().convert(ctx, game), None
            except commands.BadArgument:
                pass
        if game and not name:
            await ctx.send(f"There's no game called `{game[:40]}`. `;help` lists every game.")
            return
        if not (name or channel):
            await ctx.send(
                "Tell me what to unpin: a game (`;unsetchannel connect4`), a channel "
                "(`;unsetchannel #connect-four`), or both."
            )
            return

        lock, guild_id = self.bot.channel_lock, ctx.guild.id
        if name and channel:
            if lock.unpin_game(guild_id, name, channel.id):
                left = live_pins(self.bot, guild_id).get(name)
                still = f" It still lives in {mention_all(left)}." if left else ""
                msg = f"Unpinned `{name}` from {channel.mention}.{still}"
            else:
                msg = f"`{name}` isn't pinned to {channel.mention}."
        elif name:
            if lock.unpin_game(guild_id, name):
                msg = f"Unpinned `{name}` from every channel."
            else:
                msg = f"`{name}` isn't pinned to any channel."
        elif lock.unpin_channel(guild_id, channel.id):
            msg = f"{channel.mention} isn't limited to certain games anymore."
        else:
            msg = f"{channel.mention} doesn't have any games pinned to it."
        await ctx.send(msg)

    # --- turning the bot off in a channel ---
    @commands.hybrid_command(description="Turn the bot off in a channel (server admins only)")
    @app_commands.describe(channel="The channel to turn me off in. Leave it empty for this one")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @server_admin()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disable(self, ctx, channel: discord.TextChannel = None):
        channel = channel or _here(ctx)
        if channel is None:
            await ctx.send("Which channel? Give me its ID, like `;disable 123456789012345678`.")
            return
        lock = self.bot.channel_lock
        if lock.is_disabled(channel.id):
            await ctx.send(f"I'm already turned off in {channel.mention}.")
            return
        lock.disable(channel.id)
        await ctx.send(
            f"🔇 I'm turned off in {channel.mention} now, and in its threads too. I'll ignore commands "
            "there until an admin runs `;enable` in it."
        )

    @commands.hybrid_command(description="Turn the bot back on in a channel (server admins only)")
    @app_commands.describe(channel="The channel to turn me back on in. Leave it empty for this one")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @server_admin()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def enable(self, ctx, channel: discord.TextChannel = None):
        channel = channel or _here(ctx)
        if channel is None:
            await ctx.send("Which channel? Give me its ID, like `;enable 123456789012345678`.")
            return
        lock = self.bot.channel_lock
        if not lock.is_disabled(channel.id):
            await ctx.send(f"I'm not turned off in {channel.mention}.")
            return
        lock.enable(channel.id)
        await ctx.send(f"🔊 I'm back on in {channel.mention}.")

    # --- overview ---
    @commands.hybrid_command(
        aliases=["disabledchannels"], description="See which games are pinned where, and where I'm turned off"
    )
    @app_commands.guild_only()
    async def gamechannels(self, ctx):
        lock = self.bot.channel_lock
        if ctx.guild is None:  # the owner's view from a DM: every switched-off channel, everywhere
            if ctx.author.id != config.OWNER_ID:
                raise commands.NoPrivateMessage()
            off = lock.all()
            lines = "\n".join(f"<#{c}> (`{c}`)" for c in off)
            await ctx.send(f"Turned off in:\n{lines}" if off else "I'm not turned off anywhere.")
            return
        pins = live_pins(self.bot, ctx.guild.id)
        off = [c for c in lock.all() if ctx.guild.get_channel(c)]
        if not (pins or off):
            await ctx.send(
                "Nothing is set up here yet. Admins can pin a game with `;setchannel <game> <channel>` or turn "
                "me off in a channel with `;disable`."
            )
            return
        embed = embeds.branded(title="📌 Channel settings")
        add_lines_field(embed, "Pinned games", [f"`{g}`: {mention_all(chans)}" for g, chans in sorted(pins.items())])
        add_lines_field(embed, "Turned off in", [f"<#{c}>" for c in off])
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # A game pinned only to a deleted channel could otherwise never be played.
        self.bot.channel_lock.unpin_channel(channel.guild.id, channel.id)
        self.bot.channel_lock.enable(channel.id)


async def setup(bot):
    await bot.add_cog(ServerAdmin(bot))
