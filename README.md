# MiniGames — a Discord games bot

A multiplayer **mini-games Discord bot** built with [discord.py](https://discordpy.readthedocs.io/).
It bundles ~20 games and utilities — from Connect 4 and Blackjack to a full
cricket-match simulator — with persistent scores and leaderboards. The bot runs
sharded so it can scale across many servers, and supports both classic prefix
commands (`;`) and slash commands.

> Live on [top.gg](https://top.gg/bot/1285070559087951974).

## Features

**Games**
`dino` · `rockpaperscissors` · `connect4` · `tictactoe` · `fight` · `flagle` ·
`mathematics` · `blackjack` · `8ball` · `truthordare` · `riddle` · `race`

**Cricket**
`simulate` (full two-innings match simulation) · `livecricket` · `playcricket`

**Utility**
`profile` · `leaderboard` · `define` · `urbandictionary` · `botinfo` · `help`

Scores for competitive games are tracked per user in SQLite and surfaced through
`;leaderboard <game>` and `;profile`.

## Tech stack

- **Python 3.12**, **discord.py 2.4** (`AutoShardedBot`, app commands, UI views)
- **aiohttp** for non-blocking external API calls (dictionary, Urban Dictionary, CricAPI, flags)
- **SQLite** for score persistence
- **topggpy** for Top.gg server-count posting

## Getting started

```bash
# 1. Clone and create a virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy .env.example .env        # then edit .env with your real tokens

# 4. Run
python minigames.py
```

## Configuration

Secrets are read from environment variables (a local `.env` file is loaded
automatically). See [.env.example](.env.example):

| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | yes | Discord bot token |
| `TOPGG_TOKEN` | no | Top.gg API token (server-count posting) |
| `CRICAPI_KEY` | no | [CricAPI](https://cricapi.com/) key for `;livecricket` |

Never commit `.env` — it's git-ignored.

## Commands

Default prefix is `;` (e.g. `;help`, `;fight @user`, `;leaderboard dino`). Many
games also have slash-command equivalents. Use `;help <command>` for per-command
usage and instructions.

## Project status & architecture

This codebase is being incrementally refactored from a single-file bot toward a
modular, cog-based package. The audit and roadmap driving that work live in
[`docs/`](docs/):

- [`docs/AUDIT.md`](docs/AUDIT.md) — full code/architecture/security audit
- [`docs/REFACTOR_PLAN.md`](docs/REFACTOR_PLAN.md) — roadmap + target folder structure
- [`docs/RATE_LIMITS.md`](docs/RATE_LIMITS.md) — rate-limit prevention plan
- [`docs/GITHUB_WORKFLOW.md`](docs/GITHUB_WORKFLOW.md) — branching, CI, deployment
