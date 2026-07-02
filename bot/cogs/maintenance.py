"""Owner-only maintenance: a daily SQLite backup and command-usage logging.

The usage listeners run for everyone (that is how the counts are gathered); the
cog_check only gates the ``;usage`` command so the report stays owner-only.
"""

import asyncio
import logging
import sqlite3

from discord.ext import commands, tasks

from bot.core import config, embeds

log = logging.getLogger(__name__)

DB_PATH = "scores.db"
BACKUP_PATH = "scores.db.bak"


def _backup():
    """Copy the live database to the backup file with SQLite's online backup API,
    which is safe against a running WAL database. Blocking, so run in a thread."""
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(BACKUP_PATH)
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()


class Maintenance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_db.start()

    async def cog_check(self, ctx):
        return ctx.author.id == config.OWNER_ID  # gates ;usage; listeners still run for everyone

    def cog_unload(self):
        self.backup_db.cancel()

    # --- daily backup (also runs once on boot) ---
    @tasks.loop(hours=24)
    async def backup_db(self):
        try:
            await asyncio.to_thread(_backup)
            log.info("Database backed up to %s", BACKUP_PATH)
        except Exception:
            log.exception("Database backup failed")

    @backup_db.before_loop
    async def before_backup(self):
        await self.bot.wait_until_ready()

    # --- command usage logging ---
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.command:
            self.bot.usage.record(ctx.command.qualified_name)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction, command):
        self.bot.usage.record(command.qualified_name)

    @commands.command()
    async def usage(self, ctx, days: int = 7):
        """Most-used commands over the last N days (default 7)."""
        days = max(1, min(days, 90))
        rows = self.bot.usage.top(days=days)
        if not rows:
            await ctx.send("No command usage recorded yet.")
            return
        lines = [f"{i}. `{cmd}` - {count:,}" for i, (cmd, count) in enumerate(rows, 1)]
        embed = embeds.branded(title=f"Command usage (last {days}d)", description="\n".join(lines))
        embed.set_footer(text=f"{self.bot.usage.total(days=days):,} commands total")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Maintenance(bot))
