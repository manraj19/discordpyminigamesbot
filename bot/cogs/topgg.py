"""Top.gg integration: periodically post the guild count."""

import logging

import topgg
from discord.ext import commands, tasks

from bot.core import config

log = logging.getLogger(__name__)


class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.topggpy = topgg.DBLClient(bot, config.TOPGG_TOKEN)
        bot.topgg_client = self.topggpy  # let other cogs check votes (e.g. ;vote rewards)
        self.update_stats.start()

    @tasks.loop(minutes=60)
    async def update_stats(self):
        try:
            await self.topggpy.post_guild_count()
            log.info("Posted server count: %d", len(self.bot.guilds))
        except Exception:
            log.exception("Failed to post server count")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.update_stats.cancel()


async def setup(bot):
    if not config.TOPGG_TOKEN:
        log.info("TOPGG_TOKEN not set; Top.gg stats posting is disabled.")
        return
    await bot.add_cog(TopGG(bot))
