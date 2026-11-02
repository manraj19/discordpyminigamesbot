"""MiniGames bot package.

Layout:
- ``bot.games``    : pure game rules, NO discord.py imports (unit-testable)
- ``bot.views``    : discord UI (View/Button/Select) classes
- ``bot.services`` : data access and external integrations
- ``bot.cogs``     : thin adapters wiring prefix + slash commands to the above
"""
