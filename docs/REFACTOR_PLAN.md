# Refactor Roadmap — MiniGames Discord Bot

> Phase 2. Goal: a maintainable, multi-developer codebase that can scale toward tens of thousands of guilds, while keeping the live `minigames.py` bot working throughout.

## Priorities

### High (correctness / stability / security)
1. **Rotate all leaked secrets** (manual), then externalise to env vars + add `.gitignore`. ← PR #1
2. `git init`, untrack `.venv`/`__pycache__`/`.db`, push a clean baseline.
3. Convert all blocking `requests.get` → shared `aiohttp` session.
4. Fix `simulate` message spam → one progressively-edited message / batched embed; add `timeout=` + channel checks to its `wait_for`s.
5. Move `add_cog` to `setup_hook`; remove beta's `on_ready` global sync.
6. Collapse the `minigames`/`minibeta` split into one codebase (beta = a branch).
7. Fix `fetch_data_with_retry` unbound-`response` bug; guard `FightView.on_timeout` DMs.

### Medium (maintainability)
8. Extract a data-access layer (`aiosqlite`, one repository module); remove the global cursor.
9. De-duplicate prefix vs slash via shared core functions.
10. Move static data (countries, riddles, truth/dare, 8ball, words) into `data/*.json`.
11. Split into cogs (`cogs/games/*`, `cogs/utility.py`, `cogs/admin.py`).
12. Replace `print` with `logging`; add a cache with TTL + max size.
13. Fix `requirements.txt`; add `ruff` + `black`.

### Low (nice-to-have)
14. Unit tests for pure game logic (cricket sim, blackjack value, connect-4 win check).
15. De-dup the riddle list; centralise colors/constants.
16. Type hints + `mypy`; docstrings only where they add value.

## Proposed folder structure

```
minigames-bot/
├─ bot/
│  ├─ __main__.py            # entrypoint: config, create bot, load cogs, run
│  ├─ core/
│  │  ├─ bot.py              # AutoShardedBot subclass + setup_hook (cog load, sync strategy)
│  │  ├─ config.py           # env-based settings (token, keys, owner id, prefix)
│  │  └─ logging.py
│  ├─ cogs/
│  │  ├─ admin.py            # sync, score_summary (owner-gated)
│  │  ├─ help.py
│  │  ├─ games/              # fight, trivia, blackjack, connect4, tictactoe, rps, flagle, wordle, cricket
│  │  └─ utility.py          # define, urban, 8ball, botinfo, profile, leaderboard
│  ├─ games/                 # PURE logic, NO discord imports (unit-testable)
│  ├─ views/                 # reusable View/Button/Select classes
│  ├─ services/              # scores.py (ScoreRepository, aiosqlite), topgg.py
│  ├─ clients/               # async HTTP wrappers + shared aiohttp session + TTL cache
│  ├─ models/                # dataclasses: Score, Profile, MatchResult
│  └─ data/                  # countries.json, riddles.json, truth_dare.json, words.json
├─ tests/                    # pytest, mirrors bot/games + bot/services
├─ scripts/                  # check.py, cricsim3.py (dev tools, out of the package)
├─ .env.example  .gitignore  pyproject.toml  README.md
└─ .github/workflows/ci.yml
```

Key rule: **`bot/games/` imports zero discord.py** — game rules are pure functions; cogs are thin adapters that call them and render embeds. This is what makes prefix+slash sharing and testing possible.

## Migration strategy

**Change first (lowest risk, highest value)**
- Secrets → env + git + `.gitignore` (PR #1). No behaviour change.
- `requests` → `aiohttp` (PR #2). Same JSON, big stability win.
- `simulate` message batching + `wait_for` timeouts (PR #3).
- `setup_hook` / sync fixes (PR #4).

**Change later (structural, behind the safety net of git + the above)**
- Introduce `bot/` package and migrate **one game end-to-end** (Fight) as the template: pure logic in `bot/games/fight.py`, view in `bot/views/`, cog in `bot/cogs/games/fight.py` registering both prefix and slash from one core.
- Repeat per game; keep the old monolith importing/working until each is moved.
- Swap the global cursor for `ScoreRepository` once a game depends on it.
- Externalise static data to `data/*.json`.

**Do NOT touch initially**
- The live DB schema and the `scores.db` data (preserve compatibility).
- The production prefix `;` and existing command names/aliases.
- Game *rules/balance* (fight damage values, cricket logic) — refactor structure, not behaviour.
- Working slash commands that aren't causing problems.

**Risks per change**
- aiohttp swap: response-shape mismatch → mitigate with try/except + a manual test of each command.
- simulate batching: changes message cadence (UX) → preserve content, reduce count.
- setup_hook move: cog double-load edge cases → test reconnect.
- Package migration: import-time registration differs from monolith → migrate incrementally, one cog at a time, never big-bang.
