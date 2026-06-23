"""Blocklist enforcement for both command systems.

- ``BlockedUser`` is raised for blocked users on prefix commands (and swallowed
  silently by the error handler).
- ``BlocklistCommandTree`` rejects blocked users on slash commands.

The owner is always exempt, so you can never lock yourself out.
"""

from discord import app_commands
from discord.ext import commands

from bot.core import config


class BlockedUser(commands.CheckFailure):
    """Raised when a blocklisted user invokes a prefix command."""


class ChannelDisabled(commands.CheckFailure):
    """Raised when a command is used in a channel where the bot is disabled."""


def _is_blocked(client, user_id):
    if user_id == config.OWNER_ID:
        return False
    blocklist = getattr(client, "blocklist", None)
    return bool(blocklist and blocklist.is_blocked(user_id))


def _channel_disabled(client, channel_id, user_id):
    if user_id == config.OWNER_ID:  # owner is exempt, so you can always re-enable
        return False
    lock = getattr(client, "channel_lock", None)
    return bool(lock and lock.is_disabled(channel_id))


class BlocklistCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction):
        if _is_blocked(interaction.client, interaction.user.id):
            return False
        return not _channel_disabled(interaction.client, interaction.channel_id, interaction.user.id)


async def global_blocklist_check(ctx):
    """Global check for prefix commands: blocked users and disabled channels."""
    if _is_blocked(ctx.bot, ctx.author.id):
        raise BlockedUser()
    if _channel_disabled(ctx.bot, ctx.channel.id, ctx.author.id):
        raise ChannelDisabled()
    return True
