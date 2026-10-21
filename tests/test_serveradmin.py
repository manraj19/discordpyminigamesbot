"""Tests for the server admin channel rules: pinned games (;setchannel) and
switched-off channels (;disable)."""

from types import SimpleNamespace

from bot.core import config
from bot.core.checks import _turned_off, game_channel_block, join_and, live_pins
from bot.services.channel_lock import ChannelLockService

C4_ROOM, GAMES_ROOM, GENERAL = 1, 2, 3


def test_pinned_game_only_starts_in_its_channels():
    pins = {"connect4": {C4_ROOM, GAMES_ROOM}}
    assert game_channel_block(pins, "connect4", C4_ROOM) is None
    assert game_channel_block(pins, "connect4", GAMES_ROOM) is None
    assert game_channel_block(pins, "connect4", GENERAL) == "`connect4` lives in <#1> and <#2> on this server."


def test_pinned_channel_only_starts_its_games():
    pins = {"connect4": {C4_ROOM}, "tictactoe": {GAMES_ROOM}, "rockpaperscissors": {GAMES_ROOM}}
    assert game_channel_block(pins, "dino", C4_ROOM) == "This channel is just for `connect4`."
    assert "`rockpaperscissors` and `tictactoe`" in game_channel_block(pins, "dino", GAMES_ROOM)
    assert game_channel_block(pins, "dino", GENERAL) is None  # unpinned game, unpinned channel


def test_block_notes_never_explain_how_to_unpin():
    pins = {"connect4": {C4_ROOM}}
    for note in (game_channel_block(pins, "connect4", GENERAL), game_channel_block(pins, "dino", C4_ROOM)):
        assert "unsetchannel" not in note


def test_non_games_and_unpinned_servers_are_never_blocked():
    pins = {"connect4": {C4_ROOM}}
    assert game_channel_block(pins, "balance", C4_ROOM) is None
    assert game_channel_block(pins, "help", C4_ROOM) is None
    assert game_channel_block({}, "connect4", GENERAL) is None


def test_pins_survive_a_restart_and_unpin_cleanly(tmp_path):
    db = str(tmp_path / "pins.db")
    lock = ChannelLockService(db)
    lock.pin_game(10, "connect4", C4_ROOM)
    lock.pin_game(10, "connect4", GAMES_ROOM)
    lock.pin_game(10, "connect4", GAMES_ROOM)  # pinning twice is harmless
    lock.pin_game(10, "tictactoe", GAMES_ROOM)
    lock.close()

    lock = ChannelLockService(db)
    try:
        assert lock.game_channels(10) == {"connect4": {C4_ROOM, GAMES_ROOM}, "tictactoe": {GAMES_ROOM}}
        assert lock.game_channels(99) == {}
        assert lock.unpin_game(10, "connect4", C4_ROOM) == 1
        assert lock.unpin_channel(10, GAMES_ROOM) == 2  # clears connect4 and tictactoe from it
        assert lock.game_channels(10) == {}
        assert lock.unpin_game(10, "connect4") == 0
        assert lock.unpin_channel(10, GAMES_ROOM) == 0
    finally:
        lock.close()


def test_pins_to_channels_deleted_while_offline_are_ignored():
    lock = ChannelLockService(":memory:")
    try:
        lock.pin_game(10, "connect4", C4_ROOM)
        lock.pin_game(10, "connect4", GAMES_ROOM)
        lock.pin_game(10, "tictactoe", GAMES_ROOM)
        guild = SimpleNamespace(get_channel=lambda c: object() if c == C4_ROOM else None)  # GAMES_ROOM is gone
        client = SimpleNamespace(channel_lock=lock, get_guild=lambda gid: guild)
        assert live_pins(client, 10) == {"connect4": {C4_ROOM}}
    finally:
        lock.close()


def _member(user_id=5, admin=False):
    return SimpleNamespace(id=user_id, guild_permissions=SimpleNamespace(administrator=admin))


def test_switched_off_channels_and_their_way_back_on():
    lock = ChannelLockService(":memory:")
    try:
        lock.disable(C4_ROOM)
        client = SimpleNamespace(channel_lock=lock)
        room, thread, general = (
            SimpleNamespace(id=C4_ROOM),
            SimpleNamespace(id=99, parent_id=C4_ROOM),
            SimpleNamespace(id=GENERAL),
        )

        assert _turned_off(client, room, _member(), "connect4")
        assert _turned_off(client, thread, _member(), "connect4")  # threads follow their channel
        assert not _turned_off(client, general, _member(), "connect4")
        assert _turned_off(client, room, _member(), "enable")  # players can't flip it back
        assert _turned_off(client, room, _member(admin=True), "connect4")  # admins are switched off too
        assert not _turned_off(client, room, _member(admin=True), "enable")  # but can always turn it back on
        assert not _turned_off(client, room, _member(config.OWNER_ID), "connect4")  # the owner is exempt
    finally:
        lock.close()


def test_lists_read_as_a_sentence():
    assert join_and([]) == ""
    assert join_and(["a"]) == "a"
    assert join_and(["a", "b"]) == "a and b"
    assert join_and(["a", "b", "c"]) == "a, b and c"
