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
from bot.core.rewards import RewardResult
from bot.games.achievements import ACHIEVEMENTS
from bot.games.achievements import evaluate as evaluate_achievements
from bot.services.blocklist import BlocklistService
from bot.services.channel_lock import ChannelLockService
from bot.services.duel import DuelService
from bot.services.economy import GAME_WIN_XP, LEVEL_UP_COINS_PER, EconomyService, payout
from bot.services.quests import QuestService
from bot.services.scores import ScoreService
from bot.services.usage import UsageService

log = logging.getLogger(__name__)

EXTENSIONS = [
    "bot.cogs.admin",
    "bot.cogs.maintenance",
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
        self.usage = UsageService()
        self.quests = QuestService()
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
        Scores are per server, derived from the player's Member (0 in DMs).
        Returns a RewardResult so callers can show one uniform reward line."""
        guild_id = user.guild.id if getattr(user, "guild", None) else 0
        self.scores.record_result(user.id, str(user), score, game, guild_id)
        game_coins = payout(game, score)
        first_win = self.economy.claim_first_win(user.id, str(user)) if score > 0 else 0
        if game_coins:
            self.economy.add_coins(user.id, str(user), game_coins)
        xp = GAME_WIN_XP if score > 0 else 0
        level_up, level_bonus = (None, 0)
        if xp:
            level_up, level_bonus = self.apply_level_up(user.id, str(user), self.duel.add_xp(user.id, str(user), xp))
        new_achievements = self.award_achievements(user.id, str(user))
        quests, quest_level, quest_bonus = self._reward_quests(user, score, game_coins)
        return RewardResult(
            coins=game_coins + level_bonus + quest_bonus,
            xp=xp,
            level_up=quest_level or level_up,
            first_win_bonus=first_win,
            new_achievements=new_achievements,
            quests=quests,
        )

    def _reward_quests(self, user, score, game_coins):
        """Fire the play/win/earn quest events for a game result and merge them.
        Returns ``(completed, level_up, bonus_coins)`` for the reward line."""
        events = [("game_play", 1)]
        if score > 0:
            events.append(("game_win", 1))
        if game_coins:
            events.append(("coins_earned", game_coins))
        completed, level_up, bonus = [], None, 0
        for kind, amount in events:
            done, lvl, extra = self.quest_event(user.id, str(user), kind, amount)
            completed.extend(done)
            level_up = lvl or level_up
            bonus += extra
        return completed, level_up, bonus

    def quest_event(self, user_id, username, kind, amount):
        """Advance the user's quests for one event. Auto-claims any completions,
        credits their coins and XP, and returns ``(completed, level_up, bonus)``
        where ``completed`` is ``[(text, coins, xp), ...]`` for the reward line
        and ``bonus`` is any level-up coin bonus the quest XP earned."""
        completed = self.quests.progress(user_id, kind, amount)
        if not completed:
            return [], None, 0
        total_coins = sum(coins for _text, coins, _xp in completed)
        total_xp = sum(xp for _text, _coins, xp in completed)
        if total_coins:
            self.economy.add_coins(user_id, username, total_coins)
        level_up, bonus = (None, 0)
        if total_xp:
            level_up, bonus = self.apply_level_up(user_id, username, self.duel.add_xp(user_id, username, total_xp))
        return completed, level_up, bonus

    def apply_level_up(self, user_id, username, level_result):
        """Credit the level-up bonus for a ``(new_level, leveled_up)`` result.
        Returns ``(level_to_announce, bonus_coins)``; both falsy when no level-up."""
        new_level, leveled = level_result
        if not leveled:
            return None, 0
        bonus = new_level * LEVEL_UP_COINS_PER
        self.economy.add_coins(user_id, username, bonus)
        return new_level, bonus

    def award_achievements(self, user_id, username):
        """Grant, pay out, and return any newly earned achievements as
        ``[(name, reward), ...]``. Idempotent, so it's safe to call on play and
        whenever a profile is viewed."""
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
                name, _desc, reward, _cond = ACHIEVEMENTS[aid]
                if reward:
                    self.economy.add_coins(user_id, username, reward)
                newly.append((name, reward))
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
        self.usage.close()
        self.quests.close()
        await super().close()
