"""MiniGames bot package.

Target architecture for the incremental refactor away from the single-file
``minigames.py`` monolith. See ``docs/REFACTOR_PLAN.md``.

Layout:
- ``bot.games``    : pure game rules, NO discord.py imports (unit-testable)
- ``bot.views``    : discord UI (View/Button/Select) classes
- ``bot.services`` : data access (scores) and external integrations
- ``bot.cogs``     : thin adapters wiring prefix + slash commands to the above
"""
