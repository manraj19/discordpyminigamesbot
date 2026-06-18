# Growth and monetization plan: MiniGames bot

A 90-day, phase-by-phase plan to grow authentic, invested users and set up
monetization. Reference doc, updated as phases complete.

## Guiding principle

Installs are easy and worthless; retention is the whole game. Bot-listing sites
and bumping bring vanity installs that churn in a day. Invested users come from
progression, competition, and community. So fix retention before spending effort
on acquisition. The wedge for this bot is cricket: the full match simulator and
hand cricket are a real differentiator that generic minigames bots don't have,
and they map naturally onto cricket and South-Asian Discord communities.

Status legend: [ ] not started, [~] in progress, [x] done.

---

## Phase 0: Make it sticky (weeks 1-3)

Goal: turn one-time players into daily users before any advertising. Advertising
a leaky bucket wastes the spend.

- [ ] Daily streak and daily reward. The single biggest retention lever; "don't break your streak" pulls people back every day.
- [ ] Per-server leaderboards (scores are global today). Server-local competition is what makes server owners keep the bot.
- [ ] Ranked/ELO ladder for the PvP games (fight, connect4, tictactoe, rps). Turns one-off matches into something to grind.
- [ ] Achievements and badges. Long-tail goals.
- [ ] Profile customization (cosmetics). These are what people will later pay for, so build the free system now.
- [ ] Weekly/seasonal reset with a "season winner" announcement.

Exit check: D1 and D7 retention measurable and trending up; a meaningful share of
players run a command on two different days.

## Phase 1: Free acquisition channels (weeks 4-6)

Goal: get discoverable everywhere, with no ad spend.

- [ ] Polish bot-listing pages (already on top.gg). Add discordbotlist.com, discords.com/bots, discadia, botlist.me. Each needs a punchy description, screenshots, and GIFs (the Fight game's action gifs are shareable).
- [ ] Vote rewards: "vote on top.gg, get bonus daily currency." Creates a recurring habit and climbs listing rankings.
- [ ] Make the support server a Community server and enable Discovery. List it on disboard.org (bump every 2 hours), discord.me, and top.gg's server list.
- [ ] Welcome-on-join: when the bot joins a server, post a short "get started" message (try `;help`, `;dino`, set up `;leaderboard`).

Exit check: steady organic installs/day from listings; support-server members growing.

## Phase 2: The cricket niche wedge (weeks 7-10)

Goal: win one audience deeply instead of pitching everyone shallowly. Highest ROI.

- [ ] Join cricket Discord servers (IPL fan servers, r/Cricket's Discord, country fan communities) and South-Asian gaming servers; offer the bot genuinely.
- [ ] Post in r/Cricket and related subreddits, plus r/discordapp and r/Discord_Bots (read each one's self-promo rules first).
- [ ] Partner with a small-to-mid cricket creator or streamer for a shoutout in exchange for a custom perk.
- [ ] Post short clips (a Crash Out in Fight, a last-ball cricket finish) to TikTok, YouTube Shorts, X, and Reddit.

Exit check: a visible bump in installs traceable to cricket communities; repeat
players from those servers.

## Phase 3: Monetization rails (weeks 11-13)

Goal: build the paid layer. Real revenue only comes at scale, so set up the rails
now and don't expect much until the user base grows.

- [ ] Cosmetic/profile system finished (from Phase 0), with premium variants: profile themes, embed colors, animated badges, a Supporter role.
- [ ] Discord Premium Apps (App Subscriptions / one-time SKUs) via the Developer Portal. Discord handles payment and tax and takes roughly a 15% cut. Requires app eligibility (verified app, etc.).
- [ ] Ko-fi or Buy Me a Coffee link in `;botinfo` and the support server for early supporters (works from day one).
- [ ] Optional convenience perks (cosmetic or quality-of-life only, never pay-to-win): reduced cooldowns, extra daily rewards, an exclusive game mode or cricket "career mode."

What not to do: never sell raw competitive advantages (violates Discord ToS),
never paywall core functionality against the Developer Policy, and keep deploy
secrets out of any monetized webhook code.

Exit check: SKUs live, a working purchase flow, first supporters.

---

## Bridge feature: economy and currency

The strongest single addition for both retention and monetization. Daily coins
that players earn and spend (gamble via slots/coinflip/higher-lower, or buy
cosmetics). It is the loop that ties the games to the paid layer: daily coins
bring people back, cosmetics are what they pay for. Slot it in around Phase 0/3.

## Metrics to track throughout

- D1 and D7 retention (do people come back?)
- DAU and MAU
- Command usage by type (which games to double down on)
- Server count vs active server count
- Votes per day

The bot already posts guild count to Top.gg; add lightweight command-usage
logging so the "double down on what works" decisions are data-driven.

## Candidate games to add (ranked by impact)

1. Trivia (was in the beta; easy to port back). Highest-engagement format; categories; can be 1v1.
2. Economy + currency (see bridge feature above).
3. Hangman and Anagram/Unscramble (reuse the existing word list; cheap).
4. 2048 (button-based, very sticky solo game).
5. Higher/Lower (fast, addictive, pairs with currency).
6. Would You Rather (data-driven like Truth or Dare; trivial to add).
7. Memory / Simon Says (emoji-sequence skill game, good for streaks).
