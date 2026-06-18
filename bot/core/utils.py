"""Small shared helpers used across cogs."""

import asyncio

import discord


async def run_countdown(message, seconds, prefix=""):
    """Edit `message` once a second to tick `seconds` down to 1, so it shows a
    live "10s, 9s, 8s" countdown. Run it as a task and cancel it the moment the
    answer arrives. ponytail: ~1 edit/sec per active game; fine at this scale.
    Editing content-only leaves any embed on the message untouched."""
    sep = "  " if prefix else ""
    try:
        for remaining in range(seconds - 1, 0, -1):
            await asyncio.sleep(1)
            await message.edit(content=f"{prefix}{sep}⏳ **{remaining}s**")
    except (discord.HTTPException, asyncio.CancelledError):
        pass


def invalid_opponent(opponent, author, *, self_message="You cannot play against yourself!"):
    """Return a rejection string for an invalid PvP matchup, or None if valid."""
    if opponent == author:
        return self_message
    if opponent.bot:
        return "You cannot play against a bot!"
    return None
