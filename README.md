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

## Architecture

The bot is a small package with a strict separation of concerns, which keeps
game rules testable and lets one core back both the prefix and slash version of
each command:

```
bot/
├─ __main__.py     # entry point (python -m bot)
├─ core/           # config, bot subclass, logging, error handling, embeds, utils
├─ clients/        # shared aiohttp HTTP client
├─ services/       # scores.py — ScoreService over scores.db
├─ data/           # static game data as JSON (countries, riddles, truth/dare, …)
├─ games/          # PURE rules, no discord imports (unit-tested)
├─ views/          # discord UI (View/Button/Select) classes
└─ cogs/           # thin command adapters wiring prefix + slash to the above
```

Design notes:

- **`bot/games/` imports no discord.py**, so the rules are unit-testable in isolation.
- Each cog exposes a single `_start()`/core used by **both** the prefix and slash
  command, so the two never drift out of sync.
- All one-time setup runs in `setup_hook` (not `on_ready`, which re-fires on every
  reconnect); the command tree is synced manually via the owner-only `;sync`.
- External HTTP uses one shared, non-blocking `aiohttp` session; secrets come from
  the environment.

## Getting started

```bash
# 1. Create a virtualenv
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy .env.example .env          # then edit .env with your real tokens

# 4. Run
python -m bot
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

Default prefix is `;` (e.g. `;help`, `;fight @user`, `;leaderboard dino`). Most
games also have slash-command equivalents. Use `;help <command>` for per-command
usage and instructions.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
ruff format .         # format
pytest                # tests
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs lint, format
check, and tests on every push and pull request.

## Deployment

The bot launches with `python -m bot` from the repository root. Set the
environment variables on the host (e.g. a systemd `EnvironmentFile`, or a `.env`
file in the working directory), then:

```bash
pip install -r requirements.txt
python -m bot
```

After deploying command changes, run `;sync` once in Discord (owner only) to
refresh the slash commands.

## Background

The audit and refactor history that shaped this codebase live in [`docs/`](docs/):
[`AUDIT.md`](docs/AUDIT.md), [`REFACTOR_PLAN.md`](docs/REFACTOR_PLAN.md),
[`RATE_LIMITS.md`](docs/RATE_LIMITS.md), [`GITHUB_WORKFLOW.md`](docs/GITHUB_WORKFLOW.md).
