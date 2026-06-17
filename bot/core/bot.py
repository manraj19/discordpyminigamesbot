"""The bot subclass: wires up intents, shared services, extension loading,
and lifecycle. All one-time setup happens in ``setup_hook`` (which runs once),
never in ``on_ready`` (which fires again on every reconnect)."""

import logging

import discord
from discord.ext import commands

from bot.clients.http import HttpClient
from bot.core import config
from bot.core.checks import BlocklistCommandTree, global_blocklist_check
from bot.core.errors import setup_error_handlers
from bot.services.blocklist import BlocklistService
from bot.services.scores import ScoreService

log = logging.getLogger(__name__)

EXTENSIONS = [
    "bot.cogs.admin",
    "bot.cogs.help",
    "bot.cogs.topgg",
    "bot.cogs.utility",
    "bot.cogs.cricket",
    "bot.cogs.dino",
    "bot.cogs.mathematics",
    "bot.cogs.eight_ball",
    "bot.cogs.riddle",
    "bot.cogs.race",
    "bot.cogs.truthordare",
    "bot.cogs.wordguess",
    "bot.cogs.emojiguess",
    "bot.cogs.rps",
    "bot.cogs.tictactoe",
    "bot.cogs.connect4",
    "bot.cogs.blackjack",
    "bot.cogs.flagle",
    "bot.cogs.fight",
]


class MiniGamesBot(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=config.COMMAND_PREFIX,
            intents=intents,
            help_command=None,
            tree_cls=BlocklistCommandTree,
        )
        # Shared services (not bot.http - that name is taken by discord.py).
        self.scores = ScoreService()
        self.blocklist = BlocklistService()
        self.http_client = HttpClient()
        self.start_time = discord.utils.utcnow()

    async def setup_hook(self):
        setup_error_handlers(self)
        self.add_check(global_blocklist_check)  # blocks banned users from prefix commands
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception:
                log.exception("Failed to load extension %s", extension)

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=f"{config.COMMAND_PREFIX}help"))
        log.info("Logged in as %s (%d guilds)", self.user, len(self.guilds))

    async def close(self):
        await self.http_client.close()
        self.scores.close()
        self.blocklist.close()
        await super().close()
