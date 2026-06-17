# Repository audit report: MiniGames Discord bot

> Phase 1 of the audit, plan, refactor process.
> Production build: `minigames.py` (prefix `;`, `AutoShardedBot`, deployed on a DigitalOcean droplet).
> Beta build: `minibeta.py` (prefix `b;`, never deployed).

## 0. Inventory

| File | Lines | Role | Verdict |
|---|---|---|---|
| `minigames.py` | 2,634 | Production bot | Live monolith |
| `minibeta.py` | 3,032 | Beta bot = production + Wordle/Trivia/WhatBeatsRock/Gemini | Diverged fork |
| `words.py` | 150 | 1,777 five-letter words (Wordle) | Used by beta only |
| `cricsim3.py` | 123 | Standalone CLI cricket sim (`input()`) | Orphan, imported nowhere |
| `check.py` | 171 | One-off DB dedup/summary script | Dev utility, not part of the bot |
| `scores.db` | n/a | Live score DB (527 rows, 7 games) | Should not be in version control |
| `unique.db`, `scores_backup_*.db` | n/a | Backups and experiments | Committed binaries |

**Biggest structural problem:** `minigames.py` and `minibeta.py` are two copies of the same bot that have diverged. Every shared command exists twice and fixes don't propagate. Beta should be a *branch*, not a separate file.

## 1. Architecture

- No package, no cogs (except `TopGG`). Commands register as an import side-effect. No `setup_hook`, no extension loading.
- Global mutable singletons: `cache` (`minigames.py:17`), `conn`/`c` SQLite handles (`:276`), and `bot`, reached into directly everywhere. Nothing injectable or testable.
- Game logic, Discord I/O, persistence, and presentation are interleaved in single functions (for example `flagle` `:916` does all four).
- The only data-access abstraction is `update_score` (`:549`); everything else issues raw SQL inline.
- Cannot support multiple developers: constant conflicts in a 3,000-line file, and zero test surface.

## 2. Code quality

**Duplication (severe)**
- Whole-file duplication between the two monoliths.
- Each game is written twice per file (prefix `@bot.command()` plus slash `@bot.tree.command()`) with copy-pasted bodies.
- The 195-entry `country_code` list and `country_name` dict are duplicated 4 times and **rebuilt inside the `while True` loop every round** (`:937`).
- `generate_embed` is defined twice in `minigames.py` (`:2469`, `:2597`); the second shadows the first.

**Dead / orphan code**
- `cricsim3.py` (unused).
- `on_close` event (`:1918`): discord.py never dispatches `on_close`, so `conn.close()` never runs.
- `hello` slash command (`:215`): leftover scaffolding in production.
- `/dino` and `/playcricket` are stubs replying "removed due to rate-limit issues" (`:547`, `:1401`).

**Large units to split:** `simulate` (`:398`), `flagle` (`:916`), `FightView` plus its 6 button classes (`:2184`), and the inline data blobs (riddles `:1922`, truth/dare `:1403`).

**Naming / consistency:** owner ID `678908396845400074` hardcoded in 3 places; cooldowns as bare literals; duplicate `import asyncio` (`:3`, `:9`); inconsistent embed colors.

**Error handling**
- `fetch_data_with_retry` (`:261`) reads `response.status_code` in `except`, but `response` is unbound if `requests.get` itself raises, giving an `UnboundLocalError` inside the handler.
- `on_app_command_error` swallows unknown errors silently; app-command errors are wrapped in `CommandInvokeError`, so the `HTTPException` branch rarely matches (the real error is `error.original`).
- `print()` is used as logging throughout. No `logging`, no levels, no tracebacks.

**Async / blocking (the rate-limit root cause)**
- Blocking `requests.get` inside async commands (`:264, :1202, :1233, :1262`). Each call blocks the whole event loop (all shards and guilds). Beta's `trivia` (`:2910`) uses `aiohttp` correctly, so the fix just wasn't applied consistently.
- Blocking SQLite on the loop thread on every `execute`/`commit`.

**Races / fragility**
- One shared module-level cursor `c` is used by all commands. It's safe only because reads do `execute()` then `fetch()` with no `await` between; one inserted `await` would corrupt result sets.
- `update_score` does a SELECT then UPDATE, which is non-atomic.

**Memory / leaks**
- `cache` grows unbounded, with no TTL or eviction, so it serves stale data forever.
- `simulate`'s `bot.wait_for('message')` has no timeout, so abandoned games leak coroutines.

## 3. Discord.py

- Prefix and slash are duplicated with copy-pasted bodies; the heaviest slash commands were disabled instead of fixed.
- `FightView.on_timeout` (`:2254`) DMs both players; `user.send` raises `Forbidden` if DMs are closed, which goes unhandled in the timeout handler.
- `add_cog(TopGG(bot))` runs inside `on_ready` (`:28`). `on_ready` re-fires on every reconnect, so the cog is re-added (which raises) or duplicate `tasks.loop` instances stack up. It belongs in `setup_hook`.
- Cooldowns are scattered as literals; `8ball` and `whatbeatsrock` have none.
- **Command tree sync:** production is correct (manual owner-gated `;sync`, `:30`). Beta `:25` runs `await bot.tree.sync()` on every `on_ready`, which is a global sync on every reconnect: textbook sync abuse and a rate-limit risk.

## 4. Rate limits (ranked)

1. Blocking HTTP on the loop, which causes heartbeat delays, then a gateway drop, then a reconnect (and a re-sync in beta). This is the number-one cause.
2. `simulate` (`:448-472`): each highlight is its own `ctx.send` plus `sleep(2)`, so a match is 30-50+ messages into one channel (the limit is about 5 per 5s). This is the worst message-spam offender.
3. Beta's `on_ready` global sync.
4. `TopGG.on_guild_join`/`on_guild_remove` both call `update_stats()` (`:2628`, `:2632`) on top of the hourly loop, which spams the Top.gg API on join/leave bursts.
5. Turn-based games (`playcricket`, `race`) send 1-2 messages per turn instead of editing one.
6. No shared HTTP session, so flag images and dictionary lookups re-hit external APIs each time.

## 5. Database

- `scores(user_id, username, score, game, PK(user_id, game))`. 527 rows: dino 253, flagle 141, fight 49, rps 32, ttt 23, connect4 20, wordle 9. The volume is tiny, so the problem is the access pattern, not the size.
- A single global connection and cursor, opened at import, blocks the loop on every call.
- `username` is denormalised; `check.py` dedups by username, which is lossy when names change and can mis-attribute scores.
- The rank query (`:612`) is a full scan per game on every `profile` call, with no tie-break.
- Live `.db` files are committed to git (a data-leak and merge-corruption risk).
- Migration path: `aiosqlite` now (no schema change), and Postgres later only if it's truly needed.

## 6. Security

- **Hardcoded live secrets** committed to a public repo: Discord tokens (`minigames.py:2635`, `minibeta.py:3033`), a Top.gg JWT (`:2605`), a CricAPI key (`minibeta.py:1371`), and a Gemini key (`minibeta.py:2931`). This is critical; rotate all of them.
- No `.gitignore`; `.venv/`, `__pycache__/`, and the live `.db` are tracked.
- Owner check by magic literal in `sync`/`score_summary`.
- `simulate`'s `wait_for` has no channel check and no timeout, so it captures messages from any channel and never ends.
- `define`/`urbandictionary` interpolate user input into URLs without encoding.
- SQL is parameterised (no injection), but `game` strings are only sometimes validated.

## 7. GitHub / process

- No git locally; the remote is stale and disconnected, so development is effectively happening without version control.
- No branches, PRs, CI, `.gitignore`, README, license, tests, or linter.
- `requirements.txt` is wrong: it lists `discord` (should be `discord.py`), pins `asyncio` (a stdlib module whose PyPI backport breaks modern Python), and omits `aiohttp`, `google-generativeai`, and version pins.
