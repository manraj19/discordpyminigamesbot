# MiniGames

A multiplayer mini-games Discord bot built with [discord.py](https://discordpy.readthedocs.io/).
It has around 25 games, including Connect 4, Bomb Party, Blackjack, a turn-based duel
RPG and a full cricket-match simulator, tied together by a coin economy with daily
streaks, quests and achievements. The bot runs sharded so it can scale across many
servers, and it supports both classic prefix commands (`;`) and slash commands.

> Live on [top.gg](https://top.gg/bot/1285070559087951974).

## Features

Games:
`dino` · `rockpaperscissors` · `connect4` · `tictactoe` · `fight` · `flagle` ·
`mathematics` · `8ball` · `truthordare` · `riddle` · `race` · `wordguess` ·
`emojiguess` · `unscramble` · `guessnumber` · `bombparty`

Cricket:
`simulate` (a full two-innings match) · `playcricket`

Gambling (with MiniCoins):
`blackjack` · `coinflip` · `slots`

Duels:
`duel` (optionally with a wager) · `ranked` (ELO) · `arena` (a PvE tower) ·
`duelist` · `duelshop` · `buygear` · `buyability` · `equip` · `enhance` · `loadout` · `duelrank`

Economy and quests:
`daily` · `quests` · `balance` · `shop` · `buy` · `richest` · `achievements` · `vote`

Utility:
`profile` · `leaderboard` · `define` · `urbandictionary` · `botinfo` · `donate` · `help`

Server admins:
`setchannel` · `unsetchannel` · `disable` · `enable` · `gamechannels`

Scores are kept per server and globally in SQLite, and shown through
`;leaderboard <game> [server]` and `;profile`.

## Server admin controls

Anyone with the Administrator permission can shape where the bot plays:

- `;setchannel connect4 #connect-four` pins a game to a channel. Connect 4 then only
  starts in #connect-four, and #connect-four only starts the games pinned to it.
  Pin a game to more channels, or more games to a channel, by running it again.
- `;unsetchannel connect4` unpins a game everywhere, `;unsetchannel #connect-four`
  clears a channel, and giving both removes a single pin.
- `;disable` turns the bot off in a channel and its threads, and `;enable` turns it
  back on. `;enable` keeps working inside a switched-off channel for admins.
- `;gamechannels` shows what is set up on the server.

Each one also works as a slash command, which Discord only shows to admins.
Non-game commands such as `;help` and `;profile` work in every channel.

## Tech stack

- Python 3.12, discord.py 2.4+ (`AutoShardedBot`, app and hybrid commands, UI views)
- aiohttp for non-blocking external calls (dictionary, Urban Dictionary, Top.gg)
- SQLite (WAL mode) for scores, the economy, duels, quests and channel settings
- tabulate for the cricket scorecards

## Architecture

The bot is a small package that keeps game rules separate from Discord code, so
the rules stay testable and one core can back both the prefix and slash version
of each command:

```
bot/
├─ __main__.py     # entry point (python -m bot)
├─ core/           # config, bot subclass, checks, error handling, embeds, rewards
├─ clients/        # shared aiohttp HTTP client
├─ services/       # SQLite access: scores, economy, duels, quests, channel rules, usage
├─ data/           # static game data (countries, riddles, words, the Bomb Party dictionary)
├─ games/          # pure rules, no discord imports (unit-tested)
├─ views/          # discord UI (View/Button/Select) classes
└─ cogs/           # thin command adapters wiring prefix + slash to the above
```

Design notes:

- `bot/games/` imports no discord.py, so the rules can be unit-tested on their own.
- Each cog has a single core function used by both the prefix and slash command,
  so the two never drift apart. The server admin commands are hybrid commands,
  where one handler serves both.
- Who may run what, and where, is decided in one place (`bot/core/checks.py`) before
  any command runs: the blocklist, switched-off channels and pinned games.
- Every coin payout goes through one reward pipeline, so each game shows the same
  reward line. Walking away from a wagered game never refunds the stake.
- One-time setup runs in `setup_hook`, not `on_ready` (which re-fires on every
  reconnect). The command tree is synced manually with the owner-only `;sync`.
- External HTTP uses one shared, non-blocking aiohttp session, and secrets come
  from the environment.

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

Secrets are read from environment variables, and a local `.env` file is loaded
automatically. See [.env.example](.env.example):

| Variable | Required | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | yes | Discord bot token |
| `TOPGG_TOKEN` | no | Top.gg API token (server-count posting and vote rewards) |

Never commit `.env`. It is git-ignored.

## Commands

The default prefix is `;` (for example `;help`, `;fight @user`, `;leaderboard dino`).
Most commands also have slash versions. Use `;help <command>` or `/help` for the
usage and instructions of any command.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
ruff format .         # format
pytest                # tests
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs lint, the format
check, the tests and a smoke import on every push and pull request. A push to
`main` that passes CI deploys automatically.

## Deployment

The bot launches with `python -m bot` from the repository root. Set the
environment variables on the host (a systemd `EnvironmentFile`, or a `.env` file
in the working directory), then:

```bash
pip install -r requirements.txt
python -m bot
```

After deploying command changes, run `;sync` once in Discord (owner only) to
refresh the slash commands.
