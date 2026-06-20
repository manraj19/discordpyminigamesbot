"""Help command: a category overview plus per-command details."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import config, embeds

PREFIX = config.COMMAND_PREFIX

CATEGORIES = {
    "Games": [
        "dino",
        "rockpaperscissors",
        "connect4",
        "tictactoe",
        "fight",
        "flagle",
        "mathematics",
        "8ball",
        "truthordare",
        "riddle",
        "race",
        "wordguess",
        "emojiguess",
        "unscramble",
        "guessnumber",
    ],
    "Cricket": ["simulate", "playcricket"],
    "Gambling": ["blackjack", "coinflip", "slots"],
    "Economy": ["daily", "balance", "shop", "buy", "richest"],
    "Utility": ["profile", "leaderboard", "define", "urbandictionary", "botinfo"],
}

# Per-command help. "aliases" and "instructions" are optional.
COMMANDS = {
    "dino": {
        "desc": "Play a game of Dino Run.",
        "usage": f"{PREFIX}dino",
        "instructions": "To evade a cactus you `jump` over it and to evade a bird you `duck` under it.",
    },
    "rockpaperscissors": {
        "desc": "Play a game of Rock Paper Scissors.",
        "aliases": ["rps"],
        "usage": f"{PREFIX}rockpaperscissors <opponent>",
    },
    "tictactoe": {"desc": "Play a game of Tic Tac Toe.", "aliases": ["ttt"], "usage": f"{PREFIX}tictactoe <opponent>"},
    "connect4": {
        "desc": "Play a game of Connect 4.",
        "aliases": ["c4"],
        "usage": f"{PREFIX}connect4 <opponent>",
        "instructions": "Connect 4 dots in a row to win!",
    },
    "fight": {
        "desc": "Fight against another user.",
        "usage": f"{PREFIX}fight <opponent>",
        "instructions": "Light attack: 5-15 damage, doesn't miss\nHeavy attack: 25-30 damage, 20% miss chance\n"
        "Crash Out: 60 damage, 50/50 chance of hitting either user\nDodge: 60% success rate\n"
        "Parry: 30% success rate, deals counter-damage if successful",
    },
    "flagle": {
        "desc": "Play a flag quiz.",
        "usage": f"{PREFIX}flagle",
        "instructions": "Guess the country based on its flag.",
    },
    "mathematics": {
        "desc": "Solve mathematical problems.",
        "aliases": ["math", "maths"],
        "usage": f"{PREFIX}mathematics <category>",
        "instructions": "Categories: addition, subtraction, multiplication, division.",
    },
    "blackjack": {
        "desc": "Play Blackjack against the bot, optionally wagering coins.",
        "aliases": ["bj"],
        "usage": f"{PREFIX}blackjack [bet]",
        "instructions": "Get as close to 21 as possible without going over. `hit` to draw or `stay` to hold. "
        "Add a bet to wager coins: win pays double, a tie returns your bet.",
    },
    "coinflip": {
        "desc": "Bet coins on a coin flip.",
        "aliases": ["cf"],
        "usage": f"{PREFIX}coinflip <bet> [heads|tails]",
        "instructions": "Guess the side. A correct call pays double your bet.",
    },
    "slots": {
        "desc": "Bet coins on the slot machine.",
        "aliases": ["slot"],
        "usage": f"{PREFIX}slots <bet>",
        "instructions": "Three of a kind pays big, two of a kind returns your bet, anything else loses it.",
    },
    "8ball": {"desc": "Ask the magic 8-ball a question.", "usage": f"{PREFIX}8ball <question>"},
    "truthordare": {"desc": "Play a game of Truth or Dare.", "aliases": ["tod"], "usage": f"{PREFIX}truthordare"},
    "riddle": {"desc": "Solve a riddle.", "usage": f"{PREFIX}riddle", "instructions": "Solve the riddle to win!"},
    "race": {
        "desc": "Race against another user.",
        "usage": f"{PREFIX}race <opponent>",
        "instructions": "Type the words in `backticks` as fast as you can!",
    },
    "wordguess": {
        "desc": "Guess the hidden 5-letter word in 6 tries.",
        "aliases": ["wg"],
        "usage": f"{PREFIX}wordguess",
        "instructions": "🟩 right letter & spot · 🟨 right letter, wrong spot · ⬛ not in the word.",
    },
    "emojiguess": {
        "desc": "Guess the word or phrase from emojis.",
        "aliases": ["emoji"],
        "usage": f"{PREFIX}emojiguess",
        "instructions": "You'll get a few emojis. Type the word or phrase they represent.",
    },
    "unscramble": {
        "desc": "Unscramble the shuffled letters into a word.",
        "aliases": ["scramble"],
        "usage": f"{PREFIX}unscramble",
        "instructions": "Rearrange the jumbled letters and type the word before the timer runs out.",
    },
    "guessnumber": {
        "desc": "Guess the number between 1 and 1000.",
        "aliases": ["gn", "higherlower"],
        "usage": f"{PREFIX}guessnumber",
        "instructions": "I'll say higher or lower after each guess until you find it.",
    },
    "simulate": {
        "desc": "Simulate a game of cricket.",
        "aliases": ["sim"],
        "usage": f"{PREFIX}simulate",
        "instructions": "Enter team and player names to simulate a match. 11 players per side, comma-separated.",
    },
    "playcricket": {
        "desc": "Play a game of classic hand cricket.",
        "aliases": ["play"],
        "usage": f"{PREFIX}playcricket",
        "instructions": "Don't guess the same number as the bot!",
    },
    "daily": {
        "desc": "Claim your daily coins and build a streak.",
        "usage": f"{PREFIX}daily",
        "instructions": "Claim once a day. Consecutive days grow your streak and your reward.",
    },
    "balance": {
        "desc": "Check your coin balance.",
        "aliases": ["bal", "coins"],
        "usage": f"{PREFIX}balance",
    },
    "shop": {
        "desc": "Browse cosmetic titles you can buy with coins.",
        "usage": f"{PREFIX}shop",
        "instructions": "Buy a title with `;buy <id>`. Your equipped title shows on your profile.",
    },
    "buy": {
        "desc": "Buy a cosmetic title from the shop.",
        "usage": f"{PREFIX}buy <id>",
        "instructions": "See available titles and their ids with `;shop`.",
    },
    "richest": {
        "desc": "See the players with the most coins.",
        "aliases": ["rich", "baltop"],
        "usage": f"{PREFIX}richest",
    },
    "profile": {
        "desc": "View your profile.",
        "usage": f"{PREFIX}profile",
        "instructions": "Shows your scores and ranks in different games.",
    },
    "leaderboard": {
        "desc": "View the leaderboard for a game.",
        "aliases": ["lb"],
        "usage": f"{PREFIX}leaderboard <game>",
        "instructions": "Supported: dino, flagle, fight, connect4, rockpaperscissors, tictactoe.",
    },
    "define": {"desc": "Define a word.", "aliases": ["def"], "usage": f"{PREFIX}define <word>"},
    "urbandictionary": {
        "desc": "Get a word's definition from Urban Dictionary.",
        "aliases": ["urban"],
        "usage": f"{PREFIX}urbandictionary <word>",
    },
    "botinfo": {"desc": "Get information about the bot.", "aliases": ["bot", "info"], "usage": f"{PREFIX}botinfo"},
}

_ALIAS_TO_NAME = {alias: name for name, info in COMMANDS.items() for alias in info.get("aliases", [])}


def _overview_embed(bot):
    embed = embeds.branded(
        title="Help",
        description=f"Use `{PREFIX}help <command>` for more info on a command.\n"
        f"[Support Server]({config.SUPPORT_SERVER}) | [Top.gg Vote]({config.TOPGG_VOTE})",
    )
    for category, names in CATEGORIES.items():
        embed.add_field(name=category, value=", ".join(f"`{n}`" for n in names), inline=False)
    if bot.user:
        embed.set_thumbnail(url=bot.user.display_avatar.url)
    return embed


def _command_embed(name):
    info = COMMANDS[name]
    embed = embeds.branded(title=name.capitalize(), description=info["desc"])
    if info.get("aliases"):
        embed.add_field(name="Aliases", value=", ".join(info["aliases"]), inline=False)
    embed.add_field(name="Usage", value=info["usage"], inline=False)
    if info.get("instructions"):
        embed.add_field(name="Instructions", value=info["instructions"], inline=False)
    return embed


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_prefix(self, ctx, command_name: str = None):
        if command_name is None:
            await ctx.send(embed=_overview_embed(self.bot))
            return
        name = command_name.lower().lstrip(config.COMMAND_PREFIX)
        name = _ALIAS_TO_NAME.get(name, name)
        if name in COMMANDS:
            await ctx.send(embed=_command_embed(name))
        else:
            await ctx.send(f"No help found for `{command_name}`. Use `{PREFIX}help` for the command list.")

    @app_commands.command(name="help", description="See the list of commands.")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=_overview_embed(self.bot))


async def setup(bot):
    await bot.add_cog(Help(bot))
