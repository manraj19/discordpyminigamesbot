"""Centralised error handling for both prefix and slash commands."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import config
from bot.core.checks import BlockedUser, ChannelDisabled

log = logging.getLogger(__name__)


def setup_error_handlers(bot):
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, (BlockedUser, ChannelDisabled)):
            return  # silently ignore blocked users and disabled channels
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"I don't have that command. Try `{config.COMMAND_PREFIX}help` for the full list.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"That command needs a bit more. See `{config.COMMAND_PREFIX}help {ctx.command}`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"I couldn't read that input. See `{config.COMMAND_PREFIX}help {ctx.command}`.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This one only works in a server, not in DMs.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Hold on a sec. Try again in {error.retry_after:.1f}s.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You can't use that one.")
        else:
            log.exception("Unhandled prefix command error in %r", ctx.command, exc_info=error)
            await ctx.send("Something broke on my end. Give it another go in a moment.")

    @bot.tree.error
    async def on_app_command_error(interaction, error):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

        if isinstance(error, app_commands.CommandOnCooldown):
            await send(f"Hold on a sec. Try again in {error.retry_after:.1f}s.", ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            await send("You can't use that one right now.", ephemeral=True)
        else:
            log.exception("Unhandled app command error", exc_info=error)
            try:
                await send("Something broke on my end. Give it another go in a moment.", ephemeral=True)
            except discord.HTTPException:
                pass
