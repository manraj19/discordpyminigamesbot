# Rate-limit prevention plan: MiniGames Discord bot

Answers to the specific questions, then the action table.

## Why the bot hits Discord rate limits
1. **Blocking HTTP on the event loop.** `requests.get` runs synchronously inside async commands (`minigames.py:264, 1202, 1233, 1262`). While it waits, the *entire* loop (all shards, all guilds) is frozen: gateway heartbeats are delayed, Discord drops the connection, and the bot reconnects. This is the primary driver.
2. **Message-send spam.** `simulate` (`:448-472`) sends each cricket highlight as a separate `ctx.send` with `asyncio.sleep(2)`, so a match is 30-50+ messages into one channel (the per-channel limit is about 5 messages per 5 seconds).
3. **Blocking SQLite** on the loop on every score read/write.

## Is command-tree syncing being abused?
- **Production (`minigames.py`): no.** Sync is manual and owner-gated (`;sync`, `:30`). Correct.
- **Beta (`minibeta.py`): yes.** `await bot.tree.sync()` runs in `on_ready` (`:25`), which re-fires on every reconnect, so it does a repeated **global** sync (heavily rate-limited). Never deploy beta as-is.

## Is message spam occurring?
Yes. `simulate` is the main offender, and the turn-based games (`playcricket`, `race`) also send 1-2 messages per turn instead of editing one message.

## Are views leaking resources?
- `cache` (`:17`) grows unbounded (no TTL or eviction), which is a slow memory leak and a stale-data source.
- `simulate`'s `bot.wait_for('message')` has no timeout, so abandoned games leave coroutines waiting forever.
- Views set timeouts, but `FightView.on_timeout` (`:2254`) can throw `Forbidden` (closed DMs) and isn't guarded.

## Are interactions mishandled?
- The heaviest slash commands (`/dino`, `/playcricket`) were disabled rather than fixed.
- Several flows are one mis-ordered call away from `InteractionResponded` (calling `interaction.response.*` after the interaction is already acknowledged).
- `TopGG.on_guild_join`/`on_guild_remove` both POST the guild count immediately (`:2628`, `:2632`) on top of the hourly loop, which spams the Top.gg API on join/leave bursts.

## Action table

| Action | Fixes | Effort |
|---|---|---|
| Move `requests` to a shared `aiohttp` session | Loop freezes, heartbeat drops, the reconnect-then-resync spiral | M |
| `simulate` and turn games: edit one message, batch highlights | Per-channel message spam (worst offender) | M |
| `aiosqlite` plus a repository (no blocking DB on the loop) | Loop stalls under load | M |
| Move `add_cog` to `setup_hook`; never sync in `on_ready`; sync per-guild in a dev test guild | `tasks.loop` duplication, global-sync rate limits | S |
| Drop the `on_guild_join`/`on_guild_remove` calls to `update_stats`; rely on the hourly loop (or debounce) | Top.gg API spam | S |
| Global cache with a TTL and size cap; cache flag and dictionary lookups | Repeated external calls, unbounded memory | S |
| Add `timeout=` and channel checks to every `wait_for` | Stuck coroutines, cross-channel capture | S |
| Guard every `user.send`/`edit_message` in `on_timeout` with try/except | Unhandled `Forbidden`/`HTTPException` in timeouts | S |
