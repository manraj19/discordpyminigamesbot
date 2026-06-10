"""Owner-only administrative commands."""

from discord.ext import commands

from bot.core import config
from bot.services.scores import SUPPORTED_GAMES


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        # Gate every command in this cog to the bot owner.
        return ctx.author.id == config.OWNER_ID

    @commands.command()
    async def sync(self, ctx):
        synced = await self.bot.tree.sync()
        await ctx.send(f"Command tree synced ({len(synced)} commands).")

    @commands.command()
    async def score_summary(self, ctx):
        lines = [f"{game.capitalize()}: {self.bot.scores.count(game)} entries" for game in SUPPORTED_GAMES]
        await ctx.send("**Total Scores by Game**\n" + "\n".join(lines))


async def setup(bot):
    await bot.add_cog(Admin(bot))
