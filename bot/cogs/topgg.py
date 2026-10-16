"""Top.gg integration: post the server count once an hour.

One POST through the shared HTTP client, the same request topggpy made, so the
bot doesn't need that package. Vote checks live in the economy cog (;vote).
"""

import logging

from discord.ext import commands, tasks

from bot.core import config

log = logging.getLogger(__name__)

STATS_URL = "https://top.gg/api/bots/stats"


class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_stats.start()

    @tasks.loop(minutes=60)
    async def update_stats(self):
        count = len(self.bot.guilds)
        try:
            status = await self.bot.http_client.post_json(
                STATS_URL, {"server_count": count}, headers={"Authorization": config.TOPGG_TOKEN}
            )
        except Exception:  # an uncaught error would stop this loop for good
            log.exception("Failed to post server count to Top.gg")
            return
        if status == 200:
            log.info("Posted server count: %d", count)
        else:
            log.warning("Failed to post server count to Top.gg (status %s)", status)

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
