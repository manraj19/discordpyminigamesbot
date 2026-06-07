# GitHub Workflow Improvements — MiniGames Discord Bot

## Current state
- No git in the working copy; the remote (`github.com/manraj19/discordpyminigamesbot`) is stale and disconnected from the deployed code.
- No branches, PRs, CI, `.gitignore`, README, license, or tests.
- "Beta" is a separate *file* (`minibeta.py`) instead of a branch — the root cause of divergence.

## Target workflow

**1. Version control baseline (PR #1)**
- `git init`; add `.gitignore` (`.venv/`, `__pycache__/`, `*.db`, `.env`).
- Externalise secrets to env vars **before** the first commit so history is clean.
- Keep the live `scores.db` out of git; back it up separately (e.g. droplet cron → object storage).

**2. Branch model**
- `main` = what's deployed. Short-lived `feat/*` and `fix/*` branches → PRs → squash-merge.
- Retire the parallel-file beta approach: new features land on a branch, not a second file.

**3. Commit hygiene**
- Conventional commits (`fix:`, `feat:`, `refactor:`, `chore:`); small and reviewable.

**4. CI (`.github/workflows/ci.yml`)**
- `ruff check .` (lint), `black --check .` (format), `pytest` (logic tests), and a smoke import (`python -c "import bot"`).
- Run on every PR; block merge on failure.

**5. Project hygiene**
- `.env.example` (committed) documents required env vars.
- `README.md`: setup, run, deploy, env vars.
- `pyproject.toml` (or pinned `requirements.txt`) with correct deps: `discord.py` (not `discord`), `aiohttp`, `aiosqlite`, `tabulate`, `topggpy`, `google-generativeai`; **drop** the `asyncio` pin (stdlib).
- Add a `LICENSE`.

**6. Deployment (DigitalOcean droplet)**
- Run from environment variables (systemd service or Docker), not hardcoded values.
- Deploy = `git pull` on `main` + restart the service. Never hand-edit files on the box.
- Suggested systemd unit reads `EnvironmentFile=/etc/minigames-bot.env` so secrets live only on the host, outside the repo.
