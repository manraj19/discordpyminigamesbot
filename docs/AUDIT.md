# Repository Audit Report — MiniGames Discord Bot

> Phase 1 of the audit → plan → refactor process.
> Production build: **`minigames.py`** (prefix `;`, `AutoShardedBot`, deployed on a DigitalOcean droplet).
> Beta build: **`minibeta.py`** (prefix `b;`, never deployed).

## 0. Inventory

| File | Lines | Role | Verdict |
|---|---|---|---|
| `minigames.py` | 2,634 | Production bot | Live monolith |
| `minibeta.py` | 3,032 | Beta bot = production + Wordle/Trivia/WhatBeatsRock/Gemini | Diverged fork |
| `words.py` | 150 | 1,777 five-letter words (Wordle) | Used by beta only |
| `cricsim3.py` | 123 | Standalone CLI cricket sim (`input()`) | Orphan / dead (imported nowhere) |
| `check.py` | 171 | One-off DB dedup/summary script | Dev utility, not part of the bot |
| `scores.db` | — | Live score DB (527 rows, 7 games) | Should not be in version control |
| `unique.db`, `scores_backup_*.db` | — | Backups / experiments | Committed binaries |

**Biggest structural problem:** `minigames.py` and `minibeta.py` are two copies of the same bot that have **diverged**. Every shared command exists twice and fixes don't propagate. Beta must become a *branch*, not a separate file.

## 1. Architecture

- No package, no cogs (except `TopGG`). Commands register as an import side-effect. No `setup_hook`, no extension loading.
- Global mutable singletons: `cache` (`minigames.py:17`), `conn`/`c` SQLite handles (`:276`), and `bot` — reached into directly everywhere. Nothing injectable or testable.
- Game logic + Discord I/O + persistence + presentation are interleaved in single functions (e.g. `flagle` `:916` does all four).
- Only data-access abstraction is `update_score` (`:549`); everything else issues raw SQL inline.
- Cannot support multiple developers: constant conflicts in a 3,000-line file, zero test surface.

## 2. Code Quality

**Duplication (severe)**
- Whole-file duplication between the two monoliths.
- Each game written twice per file (prefix `@bot.command()` + slash `@bot.tree.command()`) with copy-pasted bodies.
- 195-entry `country_code` list + `country_name` dict duplicated 4× and **rebuilt inside the `while True` loop every round** (`:937`).
- `generate_embed` defined twice in `minigames.py` (`:2469`, `:2597`) — second shadows the first.

**Dead / orphan code**
- `cricsim3.py` (unused).
- `on_close` event (`:1918`) — discord.py never dispatches `on_close`, so `conn.close()` never runs.
- `hello` slash command (`:215`) — leftover scaffolding in production.
- `/dino` and `/playcricket` are stubs replying "removed due to rate-limit issues" (`:547`, `:1401`).

**Large units to split:** `simulate` (`:398`), `flagle` (`:916`), `FightView` + 6 button classes (`:2184`), inline data blobs (riddles `:1922`, truth/dare `:1403`).

**Naming / consistency:** owner ID `678908396845400074` hardcoded in 3 places; cooldowns as bare literals; duplicate `import asyncio` (`:3`, `:9`); inconsistent embed colors.

**Error handling**
- `fetch_data_with_retry` (`:261`) reads `response.status_code` in `except`, but `response` is unbound if `requests.get` itself raises → `UnboundLocalError` inside the handler.
- `on_app_command_error` swallows unknown errors silently; app-command errors are wrapped in `CommandInvokeError`, so the `HTTPException` branch rarely matches (real error is `error.original`).
- `print()` used as logging throughout; no `logging`, no levels, no tracebacks.

**Async / blocking (the rate-limit root cause)**
- Blocking `requests.get` inside async commands (`:264, :1202, :1233, :1262`). Each call blocks the **whole event loop** (all shards/guilds). Beta's `trivia` (`:2910`) uses `aiohttp` correctly — the fix just wasn't applied consistently.
- Blocking SQLite on the loop thread on every `execute`/`commit`.

**Races / fragility**
- One shared module-level cursor `c` used by all commands. Safe only because reads do `execute()`→`fetch()` with no `await` between; one inserted `await` would corrupt result sets.
- `update_score` SELECT-then-UPDATE is non-atomic.

**Memory / leaks**
- `cache` grows unbounded — no TTL/eviction; serves stale data forever.
- `simulate`'s `bot.wait_for('message')` has no timeout — abandoned games leak coroutines.

## 3. Discord.py

- Prefix/slash duplicated with copy-pasted bodies; heaviest slash commands disabled instead of fixed.
- `FightView.on_timeout` (`:2254`) DMs both players; `user.send` raises `Forbidden` if DMs are closed → unhandled in the timeout handler.
- `add_cog(TopGG(bot))` runs **inside `on_ready`** (`:28`). `on_ready` re-fires on every reconnect → cog re-added (raises) or duplicate `tasks.loop` instances. Belongs in `setup_hook`.
- Cooldowns scattered as literals; `8ball`/`whatbeatsrock` have none.
- **Command tree sync:** production is correct (manual owner-gated `;sync`, `:30`). **Beta `:25` runs `await bot.tree.sync()` on every `on_ready`** = global sync on every reconnect = textbook sync abuse / rate-limit risk.

## 4. Rate Limits (ranked)

1. Blocking HTTP on the loop → heartbeat delays → gateway drop → reconnect (→ re-sync in beta). **#1 cause.**
2. `simulate` (`:448–472`): each highlight is its own `ctx.send` + `sleep(2)`; a match = 30–50+ messages into one channel (limit ~5/5s). **Worst message-spam offender.**
3. Beta `on_ready` global sync.
4. `TopGG.on_guild_join`/`on_guild_remove` both call `update_stats()` (`:2628`, `:2632`) on top of the hourly loop → Top.gg API spam on join/leave bursts.
5. Turn-based games (`playcricket`, `race`) send 1–2 messages per turn instead of editing one.
6. No shared HTTP session; flag images + dictionary lookups re-hit external APIs each time.

## 5. Database

- `scores(user_id, username, score, game, PK(user_id, game))`. 527 rows: dino 253, flagle 141, fight 49, rps 32, ttt 23, connect4 20, wordle 9. Volume is tiny — the problem is the access pattern, not size.
- Single global connection+cursor, opened at import, blocking the loop on every call.
- `username` denormalised; `check.py` dedups by username (lossy when names change; can mis-attribute scores).
- Rank query (`:612`) is a full scan per game per `profile` call, no tie-break.
- Live `.db` files committed to git (data leak + merge-corruption risk).
- Migration path: `aiosqlite` now (no schema change), Postgres later only if truly needed.

## 6. Security

- **Hardcoded live secrets** committed to a public repo: Discord tokens (`minigames.py:2635`, `minibeta.py:3033`), Top.gg JWT (`:2605`), CricAPI key (`minibeta.py:1371`), Gemini key (`minibeta.py:2931`). **Critical — rotate all of them.**
- No `.gitignore`; `.venv/`, `__pycache__/`, live `.db` tracked.
- Owner check by magic literal in `sync`/`score_summary`.
- `simulate` `wait_for` has no channel check and no timeout (captures messages from any channel; never ends).
- `define`/`urbandictionary` interpolate user input into URLs without encoding.
- SQL is parameterised (no injection), but `game` strings are only sometimes validated.

## 7. GitHub / Process

- No git locally; remote stale and disconnected → effectively developing without version control.
- No branches/PRs/CI/`.gitignore`/README/license/tests/linter.
- `requirements.txt` wrong: lists `discord` (should be `discord.py`), pins `asyncio` (stdlib; the PyPI backport breaks modern Python), omits `aiohttp`/`google-generativeai`/version pins.
