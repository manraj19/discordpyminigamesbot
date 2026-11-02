"""Centralised error handling for both prefix and slash commands."""

import contextlib
import difflib
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.help import COMMANDS
from bot.core import config
from bot.core.checks import BlockedUser, ChannelDisabled, WrongChannel, silenced

log = logging.getLogger(__name__)


def closest_command(bot, typed):
    """The public command a mistyped one most likely meant, or None. Too short to
    tell is None too: ``;)`` and ``;-;`` are people typing, not commands."""
    typed = typed.lower()
    if len(typed) < 3:
        return None
    public = {*COMMANDS, "help"}
    names = {alias: c.name for c in bot.commands if c.name in public for alias in (c.name, *c.aliases)}
    match = difflib.get_close_matches(typed, names, n=1, cutoff=0.75)
    return names[match[0]] if match else None


def setup_error_handlers(bot):
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, BlockedUser) or (isinstance(error, ChannelDisabled) and not str(error)):
            return  # stay quiet for blocked users, and for players in a channel the bot is off in
        if isinstance(error, (ChannelDisabled, WrongChannel)):
            await ctx.send(str(error), delete_after=10)
        elif isinstance(error, commands.CommandNotFound):
            guess = closest_command(ctx.bot, ctx.invoked_with)
            if guess and not silenced(ctx):
                await ctx.send(f"I don't have that command. Did you mean `{config.COMMAND_PREFIX}{guess}`?")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("Only server admins can do that.", ephemeral=True)
        elif isinstance(error, commands.UserInputError):
            ctx.command.reset_cooldown(ctx)  # nothing ran, so a typo shouldn't cost the cooldown
            help_hint = f"See `{config.COMMAND_PREFIX}help {ctx.command}`."
            if isinstance(error, commands.MemberNotFound):
                await ctx.send(f"I couldn't find that member. Try mentioning them. {help_hint}")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"That command needs a bit more. {help_hint}")
            else:
                await ctx.send(f"I couldn't read that input. {help_hint}")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This one only works in a server, not in DMs.")
        elif isinstance(error, commands.CommandOnCooldown):
            # ephemeral only matters when a hybrid command was run as a slash command
            await ctx.send(f"Hold on a sec. Try again in {error.retry_after:.1f}s.", ephemeral=True)
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You can't use that one.", ephemeral=True)
        else:
            log.exception("Unhandled prefix command error in %r", ctx.command, exc_info=error)
            await ctx.send("Something broke on my end. Give it another go in a moment.", ephemeral=True)

    @bot.tree.error
    async def on_app_command_error(interaction, error):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message

        if isinstance(error, app_commands.CommandOnCooldown):
            await send(f"Hold on a sec. Try again in {error.retry_after:.1f}s.", ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            await send("You can't use that one right now.", ephemeral=True)
        else:
            log.exception("Unhandled app command error", exc_info=error)
            with contextlib.suppress(discord.HTTPException):
                await send("Something broke on my end. Give it another go in a moment.", ephemeral=True)
