"""Small shared helpers used across cogs."""

import asyncio
import contextlib

import discord


async def run_countdown(message, seconds, prefix="", step=1):
    """Tick `message` down for exactly `seconds`, so it shows a live "10s, 9s, 8s"
    countdown and returning means time is up. Run it as a task and cancel it the
    moment the answer arrives. Editing content-only leaves any embed untouched.

    Ticks are timed off the clock, because the edits themselves take time: a
    sleep-then-edit loop ticked every 1.2 to 1.4 seconds live and read 3s when a
    10 second timer ran out. A tick that's already out of date gets skipped.
    ponytail: one edit per `step` seconds per active game; fine at this scale.
    Pass step=2 if the game also edits this channel on its own, since a tick every
    second spends Discord's whole edit budget (about 5 per 5 seconds)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    sep = "  " if prefix else ""
    for remaining in range(seconds - step, 0, -step):
        delay = deadline - remaining - loop.time()
        if delay < 0:
            continue
        await asyncio.sleep(delay)
        with contextlib.suppress(discord.HTTPException):
            await message.edit(content=f"{prefix}{sep}⏳ **{remaining}s**")
    await asyncio.sleep(deadline - loop.time())


def invalid_opponent(opponent, author, *, self_message="You cannot play against yourself!"):
    """Return a rejection string for an invalid PvP matchup, or None if valid."""
    if opponent == author:
        return self_message
    if opponent.bot:
        return "You cannot play against a bot!"
    return None
