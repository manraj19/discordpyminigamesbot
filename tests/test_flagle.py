"""Flagle: forgiving answers, and a run that never loses an answer to a slow edit."""

import asyncio
from types import SimpleNamespace

import pytest

from bot.cogs import flagle as cog
from bot.data import COUNTRIES, COUNTRY_ALIASES
from bot.games.flagle import _NAMES, judge


@pytest.mark.parametrize(
    "guess, code",
    [
        ("USA", "US"),
        ("U.S.A.", "US"),
        ("us", "US"),
        ("america", "US"),
        ("the united states", "US"),
        ("uk", "GB"),
        ("england", "GB"),
        ("uae", "AE"),
        ("côte d'ivoire", "CI"),
        ("cote divoire", "CI"),
        ("cote d ivoire", "CI"),
        ("ivory coast", "CI"),
        ("são tomé", "ST"),
        ("sao tome & principe", "ST"),
        ("congo", "CD"),
        ("congo", "CG"),
        ("dr congo", "CD"),
        ("st. lucia", "LC"),
        ("st lucia", "LC"),
        ("st.lucia", "LC"),
        ("the bahamas", "BS"),
        ("guinea bissau", "GW"),
        ("timor leste", "TL"),
        ("east timor", "TL"),
        ("czechia", "CZ"),
        ("bosnia", "BA"),
        ("trinidad", "TT"),
        ("burma", "MM"),
        ("swaziland", "SZ"),
        ("holland", "NL"),
        ("korea", "KP"),
        ("korea", "KR"),
        ("turkiye", "TR"),
        ("  KAZAKHSTAN!!  ", "KZ"),
        # typos of the right answer
        ("kazakstan", "KZ"),
        ("phillipines", "PH"),
        ("columbia", "CO"),
        ("portgual", "PT"),
        ("newzealand", "NZ"),
        ("lybia", "LY"),
    ],
)
def test_natural_spellings_are_right(guess, code):
    assert judge(guess, code) == "right"


@pytest.mark.parametrize("code, name", COUNTRIES.items())
def test_every_country_accepts_its_own_name(code, name):
    assert judge(name, code) == "right"
    assert judge(name.upper(), code) == "right"


@pytest.mark.parametrize(
    "guess, code",
    [
        ("iran", "IQ"),
        ("iraq", "IR"),
        ("niger", "NG"),
        ("nigeria", "NE"),
        ("austria", "AU"),
        ("australia", "AT"),
        ("dominica", "DO"),
        ("sudan", "SS"),
        ("guinea", "GW"),
        ("mali", "MT"),
        ("uk", "US"),
    ],
)
def test_naming_another_country_is_wrong(guess, code):
    assert judge(guess, code) == "wrong"


@pytest.mark.parametrize("guess", ["lol", "wait what", "no way", "macau", "", "🇺🇸", "x" * 5000])
def test_things_that_are_not_countries_cost_nothing(guess):
    assert judge(guess, "KE") == "unknown"


def test_a_typo_of_a_wrong_country_is_not_a_wrong_answer():
    assert judge("nigerria", "KE") == "unknown"


def test_the_last_flags_answer_sent_again_is_a_repeat():
    assert judge("brunei", "EC", previous="BN") == "repeat"
    assert judge("brunie", "EC", previous="BN") == "repeat"
    assert judge("brunei", "BN", previous="BN") == "right"  # the right answer always wins


def test_only_the_two_ambiguous_names_belong_to_two_countries():
    assert {name for name, owners in _NAMES.items() if len(owners) > 1} == {"congo", "korea"}
    assert set(COUNTRY_ALIASES) <= set(COUNTRIES)


# --- the run itself ---
class _Message:
    def __init__(self, player, content=""):
        self.author, self.channel, self.content = player, "chan", content
        self.reactions = []
        self.deleted = None  # the delay it was deleted with

    async def add_reaction(self, emoji):
        self.reactions.append(emoji)

    async def delete(self, delay=None):
        self.deleted = delay


class _Board:
    """The game's message. ``stall`` holds up the next edit, as a rate limit does."""

    def __init__(self):
        self.edits = []
        self.stall = 0

    async def edit(self, **kwargs):
        stall, self.stall = self.stall, 0
        await asyncio.sleep(stall)
        self.edits.append(kwargs)


class _Bot:
    def __init__(self):
        self.listeners = []
        self.paid = []

    def wait_for(self, event, check=None):  # registers on the call, as discord.py does
        future = asyncio.get_running_loop().create_future()
        self.listeners.append((future, check))
        return future

    def say(self, message):
        """Deliver a message the way the gateway does: a message nobody is listening for is gone."""
        for entry in list(self.listeners):
            future, check = entry
            self.listeners.remove(entry)
            if not future.done() and check(message):
                future.set_result(message)
            elif not future.done():
                self.listeners.append(entry)
        return message

    def reward(self, player, score, game):
        self.paid.append(score)
        return SimpleNamespace(line=lambda: "")


class _Channel:
    def __init__(self, board):
        self.board = board
        self.sent = []

    def __eq__(self, other):
        return other == "chan" or other is self

    __hash__ = None

    async def send(self, content=None, embed=None):
        self.sent.append(content)
        return self.board


@pytest.fixture
def game(monkeypatch):
    """A running cog on a fixed flag order (Brunei, Ecuador, Kazakhstan, ...) with a one second clock."""
    monkeypatch.setattr(cog, "ROUND_SECONDS", 1)
    monkeypatch.setattr(cog, "FLAG_LOAD_SECONDS", 0)
    monkeypatch.setattr(cog.random, "sample", lambda codes, n: ["BN", "EC", "KZ", "DM"])
    bot, board = _Bot(), _Board()
    return SimpleNamespace(bot=bot, board=board, channel=_Channel(board), player="me", flagle=cog.Flagle(bot))


async def _tick():
    await asyncio.sleep(0.01)


def test_an_answer_during_a_stalled_edit_still_counts(game):
    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        game.board.stall = 5  # the next flag's edit is stuck behind a rate limit
        game.bot.say(_Message(game.player, "brunei"))
        await _tick()
        assert game.board.edits == []  # nothing on screen has moved yet
        game.bot.say(_Message(game.player, "ecuador"))  # and the bot is still listening
        await _tick()
        game.bot.say(_Message(game.player, "iran"))
        await run

    asyncio.run(asyncio.wait_for(scenario(), 3))
    assert game.bot.paid == [2]


def test_one_edit_per_flag_with_the_score_on_it(game):
    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        game.bot.say(_Message(game.player, "brunei"))
        await _tick()
        game.bot.say(_Message(game.player, "macau"))  # not a country: no run lost
        await _tick()
        game.bot.say(_Message(game.player, "iran"))  # a real wrong answer ends it
        await run

    asyncio.run(scenario())
    assert len(game.board.edits) == 2  # the next flag, then the final board
    assert game.board.edits[0]["embed"].title == "Flagle · Score 1"
    assert "Brunei" in game.board.edits[0]["embed"].description
    assert game.board.edits[1]["content"] == ""  # no dead countdown left behind
    assert game.board.edits[1]["embed"].title == "Flagle · Final score 1"
    assert game.bot.paid == [1]
    assert "Wrong!" in game.channel.sent[-1] and "Ecuador" in game.channel.sent[-1]


def test_sending_the_last_answer_twice_does_not_end_the_run(game):
    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        game.bot.say(_Message(game.player, "brunei"))
        await _tick()
        repeat = game.bot.say(_Message(game.player, "brunei"))
        await _tick()
        game.bot.say(_Message(game.player, "ecuador"))
        await _tick()
        game.bot.say(_Message(game.player, "iran"))
        await run
        return repeat

    repeat = asyncio.run(scenario())
    assert repeat.reactions == []  # quietly ignored
    assert game.bot.paid == [2]


def test_chat_gets_a_question_mark_and_other_people_are_ignored(game):
    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        chat = game.bot.say(_Message(game.player, "hmm"))
        await _tick()
        stranger = game.bot.say(_Message("someone else", "iran"))
        await _tick()
        game.bot.say(_Message(game.player, "iran"))
        await run
        return chat, stranger

    chat, stranger = asyncio.run(scenario())
    assert chat.reactions == ["❓"]
    assert stranger.reactions == []
    assert game.bot.paid == [0]


def test_an_answer_typed_while_the_question_mark_goes_on_still_counts(game):
    class SlowReaction(_Message):
        async def add_reaction(self, emoji):
            await asyncio.sleep(0.5)  # a slow Discord round trip
            await super().add_reaction(emoji)

    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        game.bot.say(SlowReaction(game.player, "hmm"))
        await _tick()
        game.bot.say(_Message(game.player, "brunei"))  # while the ❓ is still in flight
        await _tick()
        game.bot.say(_Message(game.player, "iran"))
        await run

    asyncio.run(asyncio.wait_for(scenario(), 3))
    assert game.bot.paid == [1]


def test_guesses_get_cleaned_up_but_the_losing_one_stays(game):
    game.channel.guild = SimpleNamespace(me="bot")
    game.channel.permissions_for = lambda member: SimpleNamespace(manage_messages=True)

    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        said = []
        for text in ("brunei", "brunei", "hmm", "iran"):
            said.append(game.bot.say(_Message(game.player, text)))
            await _tick()
        await run
        return said

    right, repeat, chat, wrong = asyncio.run(scenario())
    assert (right.deleted, repeat.deleted) == (0, 0)
    assert chat.deleted == cog.UNKNOWN_LINGER_SECONDS and chat.reactions == ["❓"]
    assert wrong.deleted is None


def test_nothing_gets_deleted_without_manage_messages(game):
    game.channel.guild = SimpleNamespace(me="bot")
    game.channel.permissions_for = lambda member: SimpleNamespace(manage_messages=False)

    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        right = game.bot.say(_Message(game.player, "brunei"))
        await _tick()
        game.bot.say(_Message(game.player, "iran"))
        await run
        return right

    assert asyncio.run(scenario()).deleted is None


def test_time_runs_out_and_the_board_stops_counting(game):
    asyncio.run(asyncio.wait_for(game.flagle._run(game.channel, game.player), 3))
    assert "Time's up!" in game.channel.sent[-1] and "Brunei" in game.channel.sent[-1]
    assert game.board.edits[-1]["content"] == ""
    assert game.bot.listeners == [] or all(f.cancelled() for f, _ in game.bot.listeners)


def test_the_clock_waits_for_the_flag_to_be_up(game):
    """A stalled edit used to eat the player's time. The clock starts after it lands."""

    async def scenario():
        run = asyncio.create_task(game.flagle._run(game.channel, game.player))
        await _tick()
        game.board.stall = 0.5
        game.bot.say(_Message(game.player, "brunei"))
        await asyncio.sleep(1.2)  # 0.5 stalled, then 0.7 of a 1 second clock
        assert not run.done()
        await run

    asyncio.run(asyncio.wait_for(scenario(), 3))
