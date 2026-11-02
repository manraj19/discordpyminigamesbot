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


def add_lines_field(embed, name, lines):
    """Add lines as one or more embed fields, splitting at Discord's 1024-char
    field limit. Continuation fields get a blank name so they read as one block."""
    chunk = []
    field_name = name
    for line in lines:
        if sum(len(x) + 1 for x in chunk) + len(line) > 1024:
            embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
            chunk, field_name = [], "​"
        chunk.append(line)
    if chunk:
        embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
