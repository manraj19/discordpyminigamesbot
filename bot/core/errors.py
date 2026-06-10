"""Centralised error handling for both prefix and slash commands."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import config
from bot.core.checks import BlockedUser

log = logging.getLogger(__name__)


def setup_error_handlers(bot):
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, BlockedUser):
            return  # silently ignore blocklisted users
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                f"That command does not exist. Use `{config.COMMAND_PREFIX}help` to see the list of commands."
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument! Use `{config.COMMAND_PREFIX}help {ctx.command}` to see usage.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument! Use `{config.COMMAND_PREFIX}help {ctx.command}` to see usage.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {error.retry_after:.1f}s.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command.")
        else:
            log.exception("Unhandled prefix command error in %r", ctx.command, exc_info=error)
            await ctx.send("An unexpected error occurred while processing the command.")

    @bot.tree.error
    async def on_app_command_error(interaction, error):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

        if isinstance(error, app_commands.CommandOnCooldown):
            await send(f"This command is on cooldown. Try again in {error.retry_after:.1f}s.", ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            await send("You can't use this command right now.", ephemeral=True)
        else:
            log.exception("Unhandled app command error", exc_info=error)
            try:
                await send("An unexpected error occurred while processing the command.", ephemeral=True)
            except discord.HTTPException:
                pass
