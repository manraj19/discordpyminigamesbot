"""A result lands exactly once, for the right player, however the clicks arrive.

Clicks go through View._dispatch_item, the path a real click takes. Every Discord
call takes a moment, so a second click lands inside the first one's round trip.
"""

import asyncio
import os
import tempfile
from types import SimpleNamespace

import discord

from bot.cogs.duel import Duel
from bot.core.rewards import RewardResult
from bot.games.connect4 import PLAYER1_PIECE
from bot.games.duel import aggregate_stats, make_combatant, new_duel
from bot.services.duel import DuelService
from bot.views.connect4 import ColumnButton, Connect4View
from bot.views.duel import DuelView
from bot.views.fight import FightView, ParryButton
from bot.views.rps import RPSView
from bot.views.tictactoe import TicTacToeView

ROUND_TRIP = 0.02


class _User:
    def __init__(self, uid, name):
        self.id, self.name, self.display_name, self.mention = uid, name, name, f"<@{uid}>"

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return getattr(other, "id", None) == self.id

    def __hash__(self):
        return self.id


A, B = _User(1, "alice"), _User(2, "bob")


class _Response:
    def __init__(self):
        self.edits, self.sends = [], []

    async def edit_message(self, **kwargs):
        await asyncio.sleep(ROUND_TRIP)
        self.edits.append(kwargs)

    async def send_message(self, *args, **kwargs):
        await asyncio.sleep(ROUND_TRIP)
        self.sends.append(args)


class _FailingResponse(_Response):
    async def edit_message(self, **kwargs):
        await asyncio.sleep(ROUND_TRIP)
        raise discord.HTTPException(SimpleNamespace(status=500, reason="hiccup"), "boom")


class _Message:
    def __init__(self):
        self.edits = []

    async def edit(self, **kwargs):
        await asyncio.sleep(ROUND_TRIP)
        self.edits.append(kwargs)


def _click(view, item, user, response=None, sink=None):
    async def followup(*args, **kwargs):
        await asyncio.sleep(ROUND_TRIP)
        (sink if sink is not None else []).append(args)

    interaction = SimpleNamespace(
        user=user, data={}, response=response or _Response(), followup=SimpleNamespace(send=followup)
    )
    view._dispatch_item(item, interaction)
    return interaction


async def _double_click(view, first, second, user):
    _click(view, first, user)
    await asyncio.sleep(ROUND_TRIP / 4)
    _click(view, second, user)
    await asyncio.sleep(ROUND_TRIP * 8)


def _recording_win():
    wins = []

    async def on_win(member):
        wins.append(member)
        return RewardResult()

    return wins, on_win


def _duel_view():
    stats = aggregate_stats(1)
    state = new_duel(make_combatant("A", stats, ["guard", "focus"]), make_combatant("B", stats, []), first=0)
    state.fighters[1].hp = 1
    ended = []

    async def on_end(widx):
        ended.append(widx)

    view = DuelView([A, B], state, on_end=on_end)
    view.render_turn()
    return view, ended


def test_duel_double_click_on_the_kill_settles_once():
    async def scenario():
        view, ended = _duel_view()
        await _double_click(view, view.children[0], view.children[1], A)
        return ended

    assert asyncio.run(scenario()) == [0]


def test_duel_failed_edit_on_the_kill_still_pays_the_winner():
    async def scenario():
        view, ended = _duel_view()
        _click(view, view.children[0], A, response=_FailingResponse())
        await asyncio.sleep(ROUND_TRIP * 4)
        return view.is_finished(), ended

    finished, ended = asyncio.run(scenario())
    assert finished  # so no timeout comes along later and forfeits the winner
    assert ended == [0]


def test_connect4_double_click_on_the_winning_move_wins_once():
    async def scenario():
        wins, on_win = _recording_win()
        view = Connect4View(A, B, on_win=on_win)
        for row in (5, 4, 3):
            view.board[row][0] = PLAYER1_PIECE
        columns = [item for item in view.children if isinstance(item, ColumnButton)]
        await _double_click(view, columns[0], columns[1], A)
        return wins

    assert asyncio.run(scenario()) == [A]


def test_tictactoe_second_tile_in_one_turn_is_refused():
    async def scenario():
        wins, on_win = _recording_win()
        view = TicTacToeView(A, B, on_win=on_win)
        view.message = _Message()
        tile = {(item._row, item._col): item for item in view.children}
        await _double_click(view, tile[(0, 0)], tile[(0, 1)], A)
        return view, wins

    view, wins = asyncio.run(scenario())
    assert sum(cell == "X" for row in view.game.board for cell in row) == 1
    assert view.current_player == B
    assert view.message.edits == []  # one edit per move, through the click itself
    assert wins == []


def test_tictactoe_double_click_on_the_winning_move_wins_once():
    async def scenario():
        wins, on_win = _recording_win()
        view = TicTacToeView(A, B, on_win=on_win)
        tile = {(item._row, item._col): item for item in view.children}
        view.game.board[0][0] = view.game.board[0][1] = "X"
        tile[(0, 0)].disabled = tile[(0, 1)].disabled = True
        await _double_click(view, tile[(0, 2)], tile[(1, 1)], A)
        return wins

    assert asyncio.run(scenario()) == [A]


def test_rps_both_players_picking_in_one_round_trip_finishes_once():
    async def scenario():
        wins, on_win = _recording_win()
        view = RPSView(A, B, on_winner=on_win)
        results = []
        rock, _paper, scissors = view.children
        _click(view, rock, A, sink=results)
        await asyncio.sleep(ROUND_TRIP / 4)
        _click(view, scissors, B, sink=results)
        await asyncio.sleep(ROUND_TRIP * 8)
        return wins, results

    wins, results = asyncio.run(scenario())
    assert wins == [A]
    assert len(results) == 1


def test_fight_double_click_on_the_finishing_parry_wins_once(monkeypatch):
    monkeypatch.setattr("bot.views.fight.random.random", lambda: 0.99)  # the parry lands

    async def scenario():
        wins, on_win = _recording_win()
        view = FightView(A, B, on_win=on_win)
        view.attacker, view.defender, view.turn = A, B, A
        await view.start_game(SimpleNamespace(response=_Response()))
        view.phase, view.turn = "defense", B
        view.attack_move = {"damage": 10, "counter_damage": 50}
        view.hp[A] = 1
        parry = next(item for item in view.children if isinstance(item, ParryButton))
        await _double_click(view, parry, parry, B)
        return wins

    assert asyncio.run(scenario()) == [B]


def _duel_service():
    return DuelService(os.path.join(tempfile.mkdtemp(), "races.db"))


def test_a_second_ranked_result_does_not_erase_the_first():
    """Two ranked duels open at once, both started from a rating of 1000."""

    async def scenario():
        service = _duel_service()
        bot = SimpleNamespace(
            duel=service,
            apply_level_up=lambda *args: (None, 0),
            award_achievements=lambda *args: [],
            quest_event=lambda *args: ([], None, 0),
        )
        cog = Duel(bot)

        async def send(*args, **kwargs):
            pass

        channel = SimpleNamespace(send=send)
        third = _User(3, "carol")
        for user in (A, B, third):
            service.get_or_create(user.id, str(user))
        await cog._settle(channel, [A, third], "ranked", 0, 1, [])  # alice loses
        after_loss = service.get(A.id)["rating"]
        await cog._settle(channel, [A, B], "ranked", 0, 0, [])  # alice then wins
        final = service.get(A.id)["rating"]
        service.close()
        return after_loss, final

    after_loss, final = asyncio.run(scenario())
    assert after_loss < 1000
    assert after_loss < final < 1020  # the old code landed on exactly 1020, as if the loss never happened


def test_ranked_board_and_season_champion_only_count_ranked_players():
    service = _duel_service()
    service.get_or_create(1, "never_played_ranked")
    service.get_or_create(2, "ranked_player")
    service.apply_match(2, "ranked_player", False, 0, new_rating=985, ranked=True)
    assert [row[0] for row in service.top(5)] == ["ranked_player"]
    assert service.reset_season()[0] == "ranked_player"
    service.close()
