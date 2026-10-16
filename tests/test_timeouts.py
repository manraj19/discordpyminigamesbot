"""Walking away from a wagered game must not get the stake back."""

import asyncio
from types import SimpleNamespace

from bot.games.duel import aggregate_stats, make_combatant, new_duel
from bot.views.blackjack import BlackjackView
from bot.views.duel import DuelView


class _Wallet:
    def __init__(self):
        self.credits = []

    def add_coins(self, user_id, username, amount):
        self.credits.append(amount)


def test_blackjack_timeout_stands_instead_of_refunding():
    async def scenario():
        wallet = _Wallet()
        view = BlackjackView(SimpleNamespace(id=1), bot=SimpleNamespace(economy=wallet), bet=100)
        view.player_hand, view.dealer_hand = [10, 5], [10, 7]  # 15 against the dealer's 17
        await view.on_timeout()
        return wallet.credits, view.settled

    credits, settled = asyncio.run(scenario())
    assert settled
    assert credits == []  # the old code refunded the 100 here


def test_blackjack_timeout_still_pays_a_winning_hand():
    async def scenario():
        wallet = _Wallet()
        view = BlackjackView(SimpleNamespace(id=1), bot=SimpleNamespace(economy=wallet), bet=100)
        view.player_hand, view.dealer_hand = [10, 9], [10, 7]  # 19 against 17
        await view.on_timeout()
        return wallet.credits

    assert asyncio.run(scenario()) == [200]


def test_duel_timeout_forfeits_the_player_on_the_clock():
    async def scenario():
        stats = aggregate_stats(1)
        state = new_duel(make_combatant("A", stats, []), make_combatant("B", stats, []), first=1)
        players = [SimpleNamespace(id=1, display_name="A"), SimpleNamespace(id=2, display_name="B")]
        ended = []

        async def on_end(widx):
            ended.append(widx)

        await DuelView(players, state, on_end=on_end).on_timeout()
        return ended

    assert asyncio.run(scenario()) == [0]  # B was due to move, so A wins rather than everyone being refunded
