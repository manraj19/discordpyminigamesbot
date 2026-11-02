"""Phases 0 and 1 of the economy plan: the coin ledger, the ;economy report, and the
changes the ledger will judge (level bonus cap, coinflip and wager burns, level HP cap)."""

import asyncio
import datetime
import os
import tempfile
from types import SimpleNamespace

from bot.cogs.admin import Admin
from bot.cogs.duel import Duel
from bot.cogs.gambling import Gambling
from bot.core.bot import MiniGamesBot
from bot.games.duel import HP_LEVEL_CAP, aggregate_stats, arena_opponent, wager_prize
from bot.games.gambling import coinflip_winnings
from bot.services.duel import DuelService
from bot.services.economy import (
    FLOW_KEEP_DAYS,
    LEVEL_UP_BONUS_CAP,
    EconomyService,
    _flow_day,
    percentile,
    top_share,
)


class _User:
    def __init__(self, uid, name):
        self.id, self.name, self.display_name, self.mention = uid, name, name, f"<@{uid}>"

    def __str__(self):
        return self.name


ALICE, BOB = _User(1, "alice"), _User(2, "bob")


def _services():
    db = os.path.join(tempfile.mkdtemp(), "flow.db")
    return EconomyService(db), DuelService(db)


def _net(economy):
    return dict(economy.flow_by_source())


# --- the ledger ---
def test_the_ledger_adds_up_to_the_wallet():
    economy, _ = _services()
    economy.claim_daily(1, "alice")
    economy.claim_first_win(1, "alice")
    economy.claim_vote(1, "alice")
    economy.add_coins(1, "alice", 5000, "game")
    assert economy.spend(1, 100, "coinflip")
    economy.add_coins(1, "alice", 195, "coinflip")
    assert economy.buy_title(1, "alice", "novice") == "bought"
    assert economy.buy_streakshield(1, "alice") == "bought"
    economy.close_stake(economy.stake(1, "alice", 200, "wager"))  # settled and lost
    economy.stake(1, "alice", 50, "blackjack")  # still open when the bot went down
    assert economy.refund_open_stakes() == 1
    assert economy.spend(1, 10**9, "gear") is False  # a refused purchase moved nothing
    assert economy.stake(1, "alice", 10**9, "wager") is None

    net = _net(economy)
    assert net == {
        "daily": 100,
        "first_win": 40,
        "vote": 250,
        "game": 5000,
        "coinflip": 95,
        "title": -100,
        "shield": -750,
        "wager": -200,
        "blackjack": 0,
    }
    assert sum(net.values()) == economy.balance(1)[0]


def test_a_streak_milestone_counts_as_daily():
    economy, _ = _services()
    start = datetime.date(2026, 6, 1)
    for day in range(7):  # day 7 pays the milestone bonus on top
        economy.claim_daily(1, "alice", today=start + datetime.timedelta(days=day))
    assert _net(economy) == {"daily": economy.balance(1)[0]}


def test_the_ledger_forgets_old_days_on_startup(tmp_path):
    db = str(tmp_path / "flow.db")
    economy = EconomyService(db)
    insert = "INSERT INTO coin_flow (day, user_id, source, coins) VALUES (?, 1, 'game', ?)"
    economy._conn.execute(insert, (_flow_day(FLOW_KEEP_DAYS + 1), 5))
    economy._conn.execute(insert, (_flow_day(FLOW_KEEP_DAYS), 7))
    economy._conn.commit()
    economy.close()
    economy = EconomyService(db)
    assert dict(economy.flow_by_source(FLOW_KEEP_DAYS + 5)) == {"game": 7}
    assert economy.flow_by_source(7) == []  # and neither day is inside a week
    economy.close()


def test_percentile_and_top_share():
    assert percentile([], 50) == 0
    assert percentile([5], 99) == 5
    assert percentile(list(range(1, 101)), 50) == 50
    assert percentile(list(range(1, 101)), 99) == 99
    assert top_share([]) == 0
    assert top_share([0, 0]) == 0
    assert top_share([10, 90]) == 0.9  # 1% of two wallets still means one wallet
    assert top_share([1] * 99 + [50, 51]) == 101 / 200  # 101 wallets round up to two


# --- the report ---
def _report(economy, duel, days=7):
    sent = []

    async def send(**kwargs):
        sent.append(kwargs["embed"])

    cog = Admin(SimpleNamespace(economy=economy, duel=duel))
    asyncio.run(Admin.economy.callback(cog, SimpleNamespace(send=send), days))
    return sent[0].title, {field.name: field.value for field in sent[0].fields}


def test_the_report_works_on_an_empty_database():
    title, fields = _report(*_services())
    assert title == "MiniCoin economy (last 7d)"
    assert all(fields.values())  # Discord refuses an embed with an empty field
    assert fields["Net by source"] == "Nothing recorded yet."


def test_the_report_reads_the_ledger():
    economy, duel = _services()
    economy.add_coins(1, "alice", 1000, "game")
    economy.add_coins(1, "alice", 5000, "admin")  # testing coins, so kept out of paid and burned
    economy.add_coins(2, "bob", 3500, "game")
    economy.add_coins(3, "carol", 100, "daily")
    assert economy.spend(2, 500, "gear")
    duel.add_xp(1, "alice", 2500)  # level 26
    duel.add_xp(2, "bob", 100)  # level 2

    title, fields = _report(economy, duel, days=1000)  # the window stops at what the ledger keeps
    assert title == f"MiniCoin economy (last {FLOW_KEEP_DAYS}d)"
    assert "`game` +4,500" in fields["Net by source"]
    assert "`gear` -500" in fields["Net by source"]
    assert "Paid 4,600 · burned 500 · 10%" in fields["Flow (admin left out)"]
    assert "3 wallets · 9,100 coins" in fields["Wallets"]
    assert "p50 3,000 · p90 6,000 · p99 6,000 · richest 6,000 · top 1% hold 66%" in fields["Wallets"]
    assert "3 moved coins" in fields["Active players"]
    assert "p50 1,000 · p90 3,500 · most 3,500" in fields["Active players"]
    assert "past 1,500: 1 · past 3,000: 1" in fields["Active players"]
    assert fields["Levels"] == "L1-9: 1 · L10-19: 0 · L20-49: 1 · L50-99: 0 · L100+: 0 · top L26"


# --- level bonus cap ---
def test_the_level_bonus_stops_at_the_cap():
    economy, _ = _services()
    bot = SimpleNamespace(economy=economy)
    assert MiniGamesBot.apply_level_up(bot, 1, "alice", (4, True)) == (4, 100)
    assert MiniGamesBot.apply_level_up(bot, 1, "alice", (10, True)) == (10, LEVEL_UP_BONUS_CAP)
    assert MiniGamesBot.apply_level_up(bot, 1, "alice", (143, True)) == (143, LEVEL_UP_BONUS_CAP)
    assert MiniGamesBot.apply_level_up(bot, 1, "alice", (143, False)) == (None, 0)
    assert _net(economy) == {"level": 100 + 2 * LEVEL_UP_BONUS_CAP}


# --- coinflip ---
def test_coinflip_winnings_round_down_but_never_to_nothing():
    assert coinflip_winnings(100) == 95
    assert coinflip_winnings(20) == 19
    assert coinflip_winnings(2) == 1
    assert coinflip_winnings(1) == 1


def test_a_coinflip_pays_and_shows_the_same_number(monkeypatch):
    economy, _ = _services()
    economy.add_coins(1, "alice", 1000, "admin")
    cog = Gambling(SimpleNamespace(economy=economy, wager_line=lambda *args: ""))
    monkeypatch.setattr("bot.cogs.gambling.random.choice", lambda options: "heads")

    assert "**+95**" in cog._coinflip(ALICE, 100, "h")
    assert economy.balance(1)[0] == 1095
    assert "lost **100**" in cog._coinflip(ALICE, 100, "t")
    assert economy.balance(1)[0] == 995
    assert "**+1**" in cog._coinflip(ALICE, 1, "h")
    assert economy.balance(1)[0] == 996
    assert _net(economy)["coinflip"] == 95 - 100 + 1


# --- duel wagers ---
def test_wager_prize_takes_the_cut_from_the_pot():
    assert wager_prize(100) == 190
    assert wager_prize(10) == 19
    assert wager_prize(1) == 2  # too small a pot to cut


def test_a_wagered_duel_burns_the_cut_and_a_draw_burns_nothing():
    economy, duel = _services()
    bot = SimpleNamespace(
        economy=economy,
        duel=duel,
        apply_level_up=lambda *args: (None, 0),
        award_achievements=lambda *args: [],
        quest_event=lambda *args: ([], None, 0),
    )
    cog = Duel(bot)
    said = []

    async def send(message):
        said.append(message)

    channel = SimpleNamespace(send=send)
    players = [ALICE, BOB]
    for player in players:
        economy.add_coins(player.id, str(player), 1000, "admin")

    def stakes():
        return [economy.stake(player.id, str(player), 100, "wager") for player in players]

    async def scenario():
        await cog._settle(channel, players, "casual", 100, 0, stakes())
        won = economy.balance(1)[0], economy.balance(2)[0], _net(economy)["wager"]
        await cog._settle(channel, players, "casual", 100, "draw", stakes())
        drew = economy.balance(1)[0], economy.balance(2)[0], _net(economy)["wager"]
        await cog._settle(channel, players, "casual", 0, 0, [])  # a friendly duel pays from nothing
        return won, drew

    won, drew = asyncio.run(scenario())
    assert won == (1090, 900, -10)
    assert drew == (1090, 900, -10)
    assert "takes **190** of the 200-MiniCoin pot" in said[0]
    assert economy.refund_open_stakes() == 0  # every stake got closed
    assert _net(economy)["duel"] == 20


# --- level HP ---
def test_level_hp_stops_at_the_cap_everywhere():
    assert aggregate_stats(HP_LEVEL_CAP - 1)["max_hp"] == 244
    assert aggregate_stats(HP_LEVEL_CAP)["max_hp"] == 252
    assert aggregate_stats(500)["max_hp"] == 252
    assert arena_opponent(3, 500)[1] == arena_opponent(3, HP_LEVEL_CAP)[1]


def test_ranked_gives_everyone_the_same_level_hp():
    _, duel = _services()
    duel.get_or_create(1, "alice")  # level 1
    duel.add_xp(2, "bob", 5000)  # level 51
    cog = Duel(SimpleNamespace(duel=duel))
    shown = []

    async def send(*args, **kwargs):
        shown.append(kwargs["view"])
        return SimpleNamespace()

    async def scenario():
        for mode in ("ranked", "casual"):
            await cog._begin(SimpleNamespace(send=send), ALICE, BOB, mode, 0, [])
            shown[-1].stop()

    asyncio.run(scenario())
    ranked, casual = ([fighter.max_hp for fighter in view.state.fighters] for view in shown)
    assert ranked == [252, 252]
    assert casual == [100, 252]
