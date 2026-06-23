"""Custom application emoji references, defined once so branded emotes render
everywhere from a single source of truth.

These are the bot's app emojis (uploaded in the Discord Developer Portal). Note:
custom emojis only render in message content, embed descriptions, and embed field
values. They do NOT render in embed titles or field names, so keep unicode there.

App emojis only render for their OWNING application. The IDs below belong to the
production "MiniGames" app, so they will show as raw ``:coin:`` text on the beta
bot and only render correctly once deployed to prod.
"""

COIN = "<:coin:1518906215520796792>"
TROPHY = "<:trophy:1518906244646178816>"
STREAK = "<:flame:1518906222013710346>"
DUEL = "<:swords:1518906242825715793>"
HEALTH = "<:heart:1518906230964355102>"
ENERGY = "<:bolt:1518906209292521563>"
SHIELD = "<:shield:1518906236681060362>"
BLEED = "<:drop:1518906220021415956>"
POISON = "<:skull:1518906238631677973>"
STUN = "<:stun:1518906240703402084>"
BATBALL = "<:batball:1518906205446082631>"
WICKET = "<:wicket:1518906246625759354>"

# Slot reel symbols, keyed by the pure-logic symbol names in bot.games.gambling.
SLOT = {
    "cherry": "<:cherry:1518906213478436927>",
    "lemon": "<:lemon:1518906232931487966>",
    "bell": "<:bell:1518906207446892724>",
    "diamond": "<:diamond:1518906217689256029>",
    "seven": "<:seven:1518906234781040710>",
}
