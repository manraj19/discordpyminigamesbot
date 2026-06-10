"""Embed helpers for a consistent look across every command.

Using these instead of building ``discord.Embed`` ad hoc guarantees the same
brand colour and footer everywhere, which is what makes the bot feel like one
coherent product rather than a pile of separately-styled commands."""

import discord

from bot.core import config


def branded(title=None, description=None, color=None):
    """A standard embed: brand colour by default, always with the footer."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=config.BRAND_COLOR if color is None else color,
    )
    embed.set_footer(text=config.FOOTER_TEXT)
    return embed


def error(description, title="Error"):
    return branded(title=title, description=description, color=config.ERROR_COLOR)


def success(description, title=None):
    return branded(title=title, description=description, color=config.SUCCESS_COLOR)
