# GitHub workflow improvements: MiniGames Discord bot

## Current state
- No git in the working copy; the remote (`github.com/manraj19/discordpyminigamesbot`) is stale and disconnected from the deployed code.
- No branches, PRs, CI, `.gitignore`, README, license, or tests.
- "Beta" is a separate *file* (`minibeta.py`) instead of a branch, which is the root cause of the divergence.

## Target workflow

**1. Version control baseline (PR #1)**
- `git init`; add `.gitignore` (`.venv/`, `__pycache__/`, `*.db`, `.env`).
- Externalise secrets to env vars **before** the first commit so the history is clean.
- Keep the live `scores.db` out of git; back it up separately (for example a droplet cron job that copies it to object storage).

**2. Branch model**
- `main` is what's deployed. Short-lived `feat/*` and `fix/*` branches become PRs, which are squash-merged.
- Retire the parallel-file beta approach: new features land on a branch, not in a second file.

**3. Commit hygiene**
- Conventional commits (`fix:`, `feat:`, `refactor:`, `chore:`), kept small and reviewable.

**4. CI (`.github/workflows/ci.yml`)**
- `ruff check .` (lint), `ruff format --check .` (format), `pytest` (logic tests), and a smoke import (`python -c "import bot"`).
- Run on every PR, and block merge on failure.

**5. Project hygiene**
- `.env.example` (committed) documents the required env vars.
- `README.md` covers setup, running, deploying, and env vars.
- `pyproject.toml` (or a pinned `requirements.txt`) with correct deps: `discord.py` (not `discord`), `aiohttp`, `aiosqlite`, `tabulate`, and `topggpy`. Drop the `asyncio` pin (it's stdlib).
- Add a `LICENSE`.

**6. Deployment (DigitalOcean droplet)**
- Run from environment variables (a systemd service or Docker), not hardcoded values.
- Deploying means `git pull` on `main` and a service restart. Never hand-edit files on the box.
- A systemd unit that reads `EnvironmentFile=/etc/minigames-bot.env` keeps secrets on the host, outside the repo.
