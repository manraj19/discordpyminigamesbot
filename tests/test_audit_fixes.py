"""One check per bug from the November audit, so none of them quietly comes back."""

import asyncio
import random
from types import SimpleNamespace

from bot.cogs.guessnumber import _is_guess
from bot.cogs.mathematics import NUMBER
from bot.core.bot import EXTENSIONS, MiniGamesBot
from bot.core.errors import closest_command
from bot.core.rewards import RewardResult
from bot.games.cricket import simulate_innings
from bot.games.riddle import is_correct
from bot.services.economy import EconomyService
from bot.services.scores import ScoreService, game_title
from bot.views.fight import ACTION_GIFS, _gif_for


def _user(uid, name):
    return SimpleNamespace(id=uid, display_name=name)


def _run_with_bot(monkeypatch, tmp_path, scenario):
    """Run ``scenario(bot)`` against a real bot with its own empty database."""
    monkeypatch.chdir(tmp_path)  # scores.db is relative to the working directory

    async def main():
        bot = MiniGamesBot()
        await bot._async_setup_hook()
        try:
            return await scenario(bot)
        finally:
            await bot.close()

    return asyncio.run(main())


def test_every_extension_loads(monkeypatch, tmp_path):
    """A cog that fails to load only logs at startup, and its commands silently vanish.
    Loading them all also trips Discord's own limits (25 choices, duplicate names)."""

    async def scenario(bot):
        for extension in EXTENSIONS:
            await bot.load_extension(extension)
        return set(bot.extensions), {command.name for command in bot.tree.get_commands()}

    loaded, slash = _run_with_bot(monkeypatch, tmp_path, scenario)
    assert loaded == set(EXTENSIONS)
    assert {"buygear", "buyability", "enhance", "equip", "loadout"} <= slash


def test_finish_match_counts_both_players_and_a_tie(monkeypatch, tmp_path):
    async def scenario(bot):
        played = []

        def quest_event(user_id, username, kind, amount):
            played.append((user_id, kind))
            return ([("Play 3 games", 40, 0)] if user_id == 2 and kind == "game_play" else []), None, 0

        bot.quest_event = quest_event
        a, b = _user(1, "alice"), _user(2, "bob")
        won = await bot.finish_match("connect4", [a, b], a)
        wins = bot.scores.top("connect4")
        played_in_win = list(played)
        played.clear()
        tied = await bot.finish_match("connect4", [a, b], None)
        return won, wins, played_in_win, tied, list(played), bot.scores.top("connect4")

    won, wins, played_in_win, tied, played_in_tie, wins_after_tie = _run_with_bot(monkeypatch, tmp_path, scenario)
    assert (1, "game_play") in played_in_win and (2, "game_play") in played_in_win
    assert won.coins > 0 and "bob:" in won.line()
    assert len(wins) == 1
    # A tie still counts as a game played, but pays nobody and scores nothing.
    assert played_in_tie == [(1, "game_play"), (2, "game_play")]
    assert tied.coins == 0 and wins_after_tie == wins


def test_a_winning_wager_unlocks_the_coin_achievement(monkeypatch, tmp_path):
    async def scenario(bot):
        user = _user(1, "alice")
        bot.economy.add_coins(user.id, str(user), 1200)
        return bot.wager_line(user, 100)

    assert "Rich" in _run_with_bot(monkeypatch, tmp_path, scenario)


def test_closest_command_only_answers_real_typos():
    flagle = SimpleNamespace(name="flagle", aliases=[])
    help_command = SimpleNamespace(name="help", aliases=["h"])
    bot = SimpleNamespace(commands=[flagle, help_command, SimpleNamespace(name="secret", aliases=[])])
    assert closest_command(bot, "flagel") == "flagle"
    assert closest_command(bot, "hlep") == "help"
    assert closest_command(bot, ")") is None  # ;) and ;-; are people talking, not commands
    assert closest_command(bot, "-;") is None
    assert closest_command(bot, "hello") is None
    assert closest_command(bot, "secre") is None  # commands missing from the help list stay hidden


def test_reward_line_carries_notes_about_other_players():
    assert RewardResult(notes=["bob: quest done"]).line() == "bob: quest done"


def test_riddle_ignores_apostrophes_and_word_gaps():
    assert is_correct("spiderman", "spider man")
    assert is_correct("spider man", "spiderman")
    assert is_correct("money doesnt grow on trees", "money doesn't grow on trees")


def test_chat_is_not_read_as_a_guess():
    assert NUMBER.fullmatch("-12.5") and NUMBER.fullmatch("3")
    assert not NUMBER.fullmatch("lol 3")
    assert _is_guess(" 500 ")
    assert not _is_guess("5000") and not _is_guess("0") and not _is_guess("hi")


def test_fight_gif_matches_the_failed_action():
    assert _gif_for("Bob failed to dodge!") == ACTION_GIFS["Dodge Fail"]
    assert _gif_for("Bob dodged it") == ACTION_GIFS["Dodge Success"]
    assert _gif_for("Bob failed to parry!") == ACTION_GIFS["Parry Fail"]
    assert _gif_for("Bob parried it") == ACTION_GIFS["Parry Success"]


def test_a_huge_bet_is_refused_rather_than_crashing(tmp_path):
    economy = EconomyService(str(tmp_path / "economy.db"))
    economy.add_coins(1, "alice", 100)
    assert economy.spend(1, 2**70) is False
    assert economy.balance(1)[0] == 100
    economy.close()


def test_scores_keep_the_best_or_add_up(tmp_path):
    scores = ScoreService(str(tmp_path / "scores.db"))
    scores.record_result(1, "alice", 5, "dino")
    scores.record_result(1, "alice", 3, "dino")
    scores.record_result(1, "alice", 5, "connect4")
    scores.record_result(1, "alice", 3, "connect4")
    scores.record_result(2, "bob", 0, "connect4")
    assert scores.user_score(1, "dino") == 5
    assert scores.user_score(1, "connect4") == 8
    assert len(scores.top("connect4")) == 1  # a score of 0 isn't a place on the board
    scores.close()
    assert game_title("connect4") == "Connect 4"
    assert game_title("dino") == "Dino"


def test_wicket_commentary_shows_the_wicket_it_describes():
    random.seed(7)
    team = [f"P{i}" for i in range(11)]
    bowlers = [f"B{i}" for i in range(11)]
    *_, events, _overs, _faced, _bowling = simulate_innings(team, bowlers, 20, 4)
    wickets = [event["wickets"] for event in events if event["kind"] == "wicket"]
    assert wickets == list(range(1, len(wickets) + 1))
