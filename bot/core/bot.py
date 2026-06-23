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
from bot.games.achievements import evaluate as evaluate_achievements
from bot.services.blocklist import BlocklistService
from bot.services.channel_lock import ChannelLockService
from bot.services.duel import DuelService
from bot.services.economy import EconomyService, payout
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
    "bot.cogs.unscramble",
    "bot.cogs.guessnumber",
    "bot.cogs.economy",
    "bot.cogs.rps",
    "bot.cogs.tictactoe",
    "bot.cogs.connect4",
    "bot.cogs.blackjack",
    "bot.cogs.gambling",
    "bot.cogs.flagle",
    "bot.cogs.fight",
    "bot.cogs.duel",
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
        self.economy = EconomyService()
        self.duel = DuelService()
        self.blocklist = BlocklistService()
        self.channel_lock = ChannelLockService()
        self.http_client = HttpClient()
        self.topgg_client = None  # set by the Top.gg cog when a token is configured
        self.active_sessions = set()  # user ids currently in a chat-based game (one at a time)
        self.start_time = discord.utils.utcnow()

    def begin_session(self, user_id):
        """Claim a game slot for a user. Returns False if they're already playing,
        so a second game can't stack onto the same player's message stream."""
        if user_id in self.active_sessions:
            return False
        self.active_sessions.add(user_id)
        return True

    def end_session(self, user_id):
        self.active_sessions.discard(user_id)

    async def setup_hook(self):
        setup_error_handlers(self)
        self.add_check(global_blocklist_check)  # blocks banned users from prefix commands
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception:
                log.exception("Failed to load extension %s", extension)

    def reward(self, user, score, game):
        """Record a game result and pay out coins for it (the economy faucet).
        One choke point so every game earns coins with a single, tunable formula.
        Scores are per server, derived from the player's Member (0 in DMs)."""
        guild_id = user.guild.id if getattr(user, "guild", None) else 0
        self.scores.record_result(user.id, str(user), score, game, guild_id)
        coins = payout(game, score)
        if coins:
            self.economy.add_coins(user.id, str(user), coins)
        self.award_achievements(user.id, str(user))
        return coins

    def award_achievements(self, user_id, username):
        """Grant any newly earned achievements. Returns the list of new ids.
        Idempotent, so it's safe to call on play and whenever a profile is viewed."""
        duelist = self.duel.get(user_id)
        coins, streak = self.economy.balance(user_id)
        stats = {
            "total_score": self.scores.total_user_score(user_id),
            "coins": coins,
            "streak": streak,
            "duel_wins": duelist["wins"] if duelist else 0,
            "duel_rating": duelist["rating"] if duelist else 1000,
        }
        newly = []
        for aid in evaluate_achievements(stats):
            if not self.economy.has_achievement(user_id, aid):
                self.economy.grant_achievement(user_id, aid)
                newly.append(aid)
        return newly

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name=f"{config.COMMAND_PREFIX}help"))
        log.info("Logged in as %s (%d guilds)", self.user, len(self.guilds))

    async def close(self):
        await self.http_client.close()
        self.scores.close()
        self.economy.close()
        self.duel.close()
        self.blocklist.close()
        self.channel_lock.close()
        await super().close()
