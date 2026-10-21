"""Who may run what, where, for both command systems.

- Blocked users are ignored everywhere.
- In a channel a server admin turned the bot off in (``;disable``), commands are
  ignored, except ``;enable`` from an admin so the switch can be flipped back.
- Games a server admin pinned with ``;setchannel`` only start in their channels,
  and a channel with games pinned to it only starts those games.

Threads follow their parent channel's rules. The owner is exempt from the
blocklist and switched-off channels, so you can never lock yourself out.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.help import GAMES
from bot.core import config

OFF_NOTE = "I'm turned off in this channel."


class BlockedUser(commands.CheckFailure):
    """Raised when a blocklisted user invokes a prefix command."""


class ChannelDisabled(commands.CheckFailure):
    """Raised when a command is used in a channel the bot is turned off in. The
    message is empty for players (the bot stays quiet) and tells admins how to
    turn it back on."""


class WrongChannel(commands.CheckFailure):
    """Raised when a game is started outside the channels it was pinned to. The
    message says where it can be played."""


def _is_blocked(client, user_id):
    if user_id == config.OWNER_ID:
        return False
    blocklist = getattr(client, "blocklist", None)
    return bool(blocklist and blocklist.is_blocked(user_id))


def _is_admin(user):
    perms = getattr(user, "guild_permissions", None)
    return bool(perms and perms.administrator)


def _root(channel):
    """The channel a rule applies to: a thread follows its parent channel."""
    return getattr(channel, "parent_id", None) or channel.id


def _turned_off(client, channel, user, command):
    """True if the bot is off in this channel for this command. Admins can still
    run ;enable there, or they could never switch it back on."""
    lock = getattr(client, "channel_lock", None)
    if user.id == config.OWNER_ID or not (lock and channel) or not lock.is_disabled(_root(channel)):
        return False
    return not (command == "enable" and _is_admin(user))


def _off_note(user, prefix):
    if _is_admin(user):
        return f"{OFF_NOTE} Run `{prefix}enable` here to turn me back on."
    return OFF_NOTE


def silenced(ctx):
    """Whether the bot should stay quiet for this message, even about a command
    it doesn't recognise."""
    return _is_blocked(ctx.bot, ctx.author.id) or _turned_off(ctx.bot, ctx.channel, ctx.author, "")


def join_and(items):
    """``a``, ``a and b``, ``a, b and c``."""
    items = list(items)
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


def mention_all(channel_ids):
    return join_and(f"<#{c}>" for c in sorted(channel_ids))


def live_pins(client, guild_id):
    """A server's pins as ``{game: {channel ids}}``, minus channels that no longer
    exist. The delete listener removes pins as channels go, so this only matters
    for a channel deleted while the bot was offline."""
    pins = client.channel_lock.game_channels(guild_id)
    guild = client.get_guild(guild_id)
    if not pins or guild is None:
        return pins
    live = {game: {c for c in chans if guild.get_channel(c)} for game, chans in pins.items()}
    return {game: chans for game, chans in live.items() if chans}


def game_channel_block(pins, game, channel_id):
    """Why ``game`` can't start in ``channel_id`` under a server's pins, or None if
    it can. It only says where to play, never how to undo the pin: that's for
    admins to find in ``;help``, not for every player who bumps into it."""
    if game not in GAMES:
        return None
    homes = pins.get(game)
    if homes and channel_id not in homes:
        return f"`{game}` lives in {mention_all(homes)} on this server."
    pinned_here = sorted(g for g, chans in pins.items() if channel_id in chans)
    if pinned_here and game not in pinned_here:
        return f"This channel is just for {join_and(f'`{g}`' for g in pinned_here)}."
    return None


def _game_block(client, guild_id, channel, game):
    if not (getattr(client, "channel_lock", None) and guild_id and channel):
        return None
    return game_channel_block(live_pins(client, guild_id), game, _root(channel))


class BlocklistCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction):
        client, user, channel = interaction.client, interaction.user, interaction.channel
        if _is_blocked(client, user.id):
            return False
        command = interaction.command.qualified_name if interaction.command else ""
        if _turned_off(client, channel, user, command):
            note = _off_note(user, "/")
        else:
            note = _game_block(client, interaction.guild_id, channel, command)
        # Only the person who ran it sees why, so nobody else's channel gets noisy.
        if note and interaction.type is discord.InteractionType.application_command:
            await interaction.response.send_message(note, ephemeral=True)
        return note is None


async def global_blocklist_check(ctx):
    """Global check for prefix commands: blocked users, switched-off channels and
    games pinned to other channels."""
    if _is_blocked(ctx.bot, ctx.author.id):
        raise BlockedUser()
    command = ctx.command.qualified_name
    if _turned_off(ctx.bot, ctx.channel, ctx.author, command):
        # Players get silence, since a switched-off channel should stay quiet.
        raise ChannelDisabled(_off_note(ctx.author, ";") if _is_admin(ctx.author) else "")
    reason = _game_block(ctx.bot, ctx.guild and ctx.guild.id, ctx.channel, command)
    if reason:
        raise WrongChannel(reason)
    return True
