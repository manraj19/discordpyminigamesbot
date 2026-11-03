# Contributing

Thanks for wanting to help. New games, fixes and ideas are all welcome.

## How it works

1. Fork the repo and make a branch off `main`.
2. Set up locally (see [Getting started](README.md#getting-started)). Use your own
   test bot token in `.env`, never a real one in code.
3. Make your change, then run the same checks CI runs:

   ```bash
   pip install -r requirements-dev.txt
   ruff check .
   ruff format .
   pytest
   ```

4. Open a pull request against `main` and say what it does and how you tested it.

Nobody pushes to `main` directly. Every change goes through a pull request and
gets reviewed before it's merged, and merging to `main` deploys to the live bot,
so reviews can take a little while.

## Ground rules

- Don't commit `.env`, tokens, or any `.db` files. Stage files by name rather than
  with `git add -A`.
- Keep SQL parameterized. Never build a query from user input.
- Any game that takes a bet must go through `economy.stake()` so a restart can
  refund it.
- Bigger changes (a new game, economy changes): open an issue first so we can
  agree on the idea before you build it.

## Reporting a security problem

Please don't open a public issue for anything that could be abused (coin dupes,
ways to ping everyone, leaked data). Use the repo's **Security > Report a
vulnerability** button instead so it stays private until it's fixed.
