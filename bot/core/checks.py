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


def _is_blocked(client, user_id):
    if user_id == config.OWNER_ID:
        return False
    blocklist = getattr(client, "blocklist", None)
    return bool(blocklist and blocklist.is_blocked(user_id))


class BlocklistCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction):
        return not _is_blocked(interaction.client, interaction.user.id)


async def global_blocklist_check(ctx):
    """Global check for prefix commands."""
    if _is_blocked(ctx.bot, ctx.author.id):
        raise BlockedUser()
    return True
