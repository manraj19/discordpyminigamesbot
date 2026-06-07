# Rate-Limit Prevention Plan — MiniGames Discord Bot

Answers to the specific questions, then the action table.

## Why the bot hits Discord rate limits
1. **Blocking HTTP on the event loop.** `requests.get` runs synchronously inside async commands (`minigames.py:264, 1202, 1233, 1262`). While it waits, the *entire* loop (all shards, all guilds) is frozen — gateway heartbeats are delayed, Discord drops the connection, the bot reconnects. This is the primary driver.
2. **Message-send spam.** `simulate` (`:448–472`) sends each cricket highlight as a separate `ctx.send` with `asyncio.sleep(2)` — 30–50+ messages per match into one channel (per-channel limit ≈ 5 msgs / 5 s).
3. **Blocking SQLite** on the loop on every score read/write.

## Is command-tree syncing being abused?
- **Production (`minigames.py`): no.** Sync is manual and owner-gated (`;sync`, `:30`). Correct.
- **Beta (`minibeta.py`): yes.** `await bot.tree.sync()` runs in `on_ready` (`:25`), which re-fires on every reconnect → repeated **global** syncs (heavily rate-limited). Never deploy beta as-is.

## Is message spam occurring?
Yes — `simulate` is the main offender; turn-based games (`playcricket`, `race`) also send 1–2 messages per turn instead of editing one message.

## Are views leaking resources?
- `cache` (`:17`) grows unbounded (no TTL/eviction) — a slow memory leak and stale-data source.
- `simulate`'s `bot.wait_for('message')` has no timeout → abandoned games leave coroutines waiting forever.
- Views set timeouts, but `FightView.on_timeout` (`:2254`) can throw `Forbidden` (closed DMs) and isn't guarded.

## Are interactions mishandled?
- Heaviest slash commands (`/dino`, `/playcricket`) were disabled rather than fixed.
- Several flows are one mis-ordered call from `InteractionResponded` (calling `interaction.response.*` after the interaction is already acknowledged).
- `TopGG.on_guild_join`/`on_guild_remove` both POST guild count immediately (`:2628`, `:2632`), on top of the hourly loop → Top.gg API spam on join/leave bursts.

## Action table

| Action | Fixes | Effort |
|---|---|---|
| `requests` → shared `aiohttp` session | Loop freezes, heartbeat drops, reconnect→re-sync spiral | M |
| `simulate`/turn games: edit one message, batch highlights | Per-channel message spam (worst offender) | M |
| `aiosqlite` + repository (no blocking DB on loop) | Loop stalls under load | M |
| `add_cog` → `setup_hook`; never sync in `on_ready`; per-guild sync in a dev test guild | `tasks.loop` duplication, global-sync rate limits | S |
| Drop `on_guild_join/remove → update_stats`; rely on hourly loop (or debounce) | Top.gg API spam | S |
| Global cache with TTL + size cap; cache flag/dictionary lookups | Repeated external calls, unbounded memory | S |
| Add `timeout=` + channel checks to all `wait_for` | Stuck coroutines, cross-channel capture | S |
| Guard all `user.send`/`edit_message` in `on_timeout` with try/except | Unhandled `Forbidden`/`HTTPException` in timeouts | S |
