"""The page-turning buttons, and the long outputs that were split up or tidied."""

import asyncio
from types import SimpleNamespace

import discord

from bot.cogs.cricket import _table
from bot.cogs.duel import Duel
from bot.cogs.economy import Economy
from bot.cogs.utility import Utility
from bot.games.achievements import ACHIEVEMENTS
from bot.games.duel import ABILITIES, GEAR
from bot.views.duel import ability_heading, rules_pages
from bot.views.pages import PagedView, chunked


class _Interaction:
    def __init__(self, user_id):
        self.user = SimpleNamespace(id=user_id)
        self.shown, self.notes = [], []
        self.response = SimpleNamespace(edit_message=self._edit, send_message=self._note)

    async def _edit(self, embed, view):
        self.shown.append(embed.title)

    async def _note(self, text, ephemeral):
        self.notes.append(text)


def _fits_discord(embed):
    assert len(embed) <= 6000
    assert len(embed.fields) <= 25
    assert len(embed.description or "") <= 4096
    assert all(0 < len(field.name) <= 256 and 0 < len(field.value) <= 1024 for field in embed.fields)


def _pages(*names):
    return [(name, discord.Embed(title=name)) for name in names]


def test_buttons_wrap_around_and_name_where_they_lead():
    async def scenario():
        view = PagedView(1, _pages("A", "B", "C"))
        assert (view.back.label, view.forward.label) == ("◀ C", "B ▶")
        click = _Interaction(1)
        await view.forward.callback(click)
        assert (view.back.label, view.forward.label) == ("◀ A", "C ▶")
        await view.forward.callback(click)
        await view.forward.callback(click)  # past the last page, back to the first
        await view.back.callback(click)  # and the other way
        assert click.shown == ["B", "C", "A", "C"]

    asyncio.run(scenario())


def test_only_the_owner_turns_the_pages():
    async def scenario():
        view = PagedView(1, _pages("A", "B"))
        stranger = _Interaction(2)
        assert not await view.interaction_check(stranger)
        assert "Run the command yourself" in stranger.notes[0]
        assert await view.interaction_check(_Interaction(1))

    asyncio.run(scenario())


def test_footers_count_pages_and_keep_their_own_text():
    async def scenario():
        pages = _pages("A", "B")
        pages[1][1].set_footer(text="Blame Urban Dictionary.")
        PagedView(1, pages)
        assert pages[0][1].footer.text == "Page 1 of 2"
        assert pages[1][1].footer.text == "Page 2 of 2 · Blame Urban Dictionary."

    asyncio.run(scenario())


def test_one_page_gets_no_buttons_or_page_count():
    async def scenario():
        pages = _pages("A")
        view = PagedView(1, pages)
        assert view.children == []
        assert pages[0][1].footer.text is None
        await view.on_timeout()  # nothing to switch off, and no message to edit

    asyncio.run(scenario())


def test_send_keeps_the_message_so_a_timeout_can_switch_the_buttons_off():
    class Target:
        async def send(self, **kwargs):
            self.sent = kwargs
            return "the message"

    async def scenario():
        view, ctx = PagedView(1, _pages("A", "B")), Target()
        await view.send(ctx)
        assert view.message == "the message"
        assert ctx.sent["view"] is view

    asyncio.run(scenario())


class _SlashCommand(discord.Interaction):
    """Enough of an interaction to tell a fresh reply from a deferred one."""

    def __init__(self, deferred):
        self.sent = []
        self.response = SimpleNamespace(is_done=lambda: deferred, send_message=self._reply)
        self.followup = SimpleNamespace(send=self._follow_up)

    async def _reply(self, **kwargs):
        self.sent.append(("reply", kwargs["ephemeral"]))

    async def _follow_up(self, **kwargs):
        self.sent.append(("follow up", kwargs["ephemeral"]))
        return "the follow up"

    async def original_response(self):
        return "the reply"


def test_send_handles_a_slash_command_deferred_or_not():
    async def scenario():
        fresh, view = _SlashCommand(deferred=False), PagedView(1, _pages("A", "B"))
        await view.send(fresh, ephemeral=True)
        assert fresh.sent == [("reply", True)]
        assert view.message == "the reply"

        deferred, view = _SlashCommand(deferred=True), PagedView(1, _pages("A", "B"))
        await view.send(deferred)
        assert deferred.sent == [("follow up", False)]
        assert view.message == "the follow up"

    asyncio.run(scenario())


def _shop_pages():
    duel = SimpleNamespace(
        get_or_create=lambda *_: {"weapon": "warblade", "armor": None, "accessory": None, "loadout": ["mend"]},
        gear_levels=lambda _: {"warblade": 2},
        owned_gear=lambda _: ["warblade", "chainmail"],
        unlocked_abilities=lambda _: ["mend", "venom"],
    )
    economy = SimpleNamespace(balance=lambda _: (1234, 0))
    self = SimpleNamespace(bot=SimpleNamespace(duel=duel, economy=economy))
    return Duel._shop_pages(self, SimpleNamespace(id=1))


def test_the_duel_shop_lists_everything_once_and_fits():
    pages = _shop_pages()
    names = [name for name, _embed in pages]
    assert names[:3] == ["Weapons", "Armor", "Accessories"]
    assert len(names) == len(set(names))  # a button can't lead to two pages with one name
    shelves = [field.name for _name, embed in pages for field in embed.fields]
    buyable = [ability_heading(ab) for ab in ABILITIES.values() if ab.price]
    assert sorted(shelves) == sorted([gear["name"] for gear in GEAR.values()] + buyable)
    for _name, embed in pages:
        _fits_discord(embed)
        assert "**1,234**" in embed.description


def test_the_duel_shop_offers_the_next_step_for_each_item():
    entries = {field.name: field.value for _name, embed in _shop_pages() for field in embed.fields}
    assert "✅ Equipped +2 · `;enhance warblade`" in entries["Warblade"]
    assert "✅ Owned · `;equip chainmail`" in entries["Chainmail"]
    assert "600" in entries["Steel Sword"] and "`;buygear steel_sword`" in entries["Steel Sword"]
    assert "+9 defense, +25 HP, -1 energy" in entries["Juggernaut Plate"]
    assert "✅ In your loadout" in entries[ability_heading(ABILITIES["mend"])]
    assert "✅ Unlocked · `;loadout`" in entries[ability_heading(ABILITIES["venom"])]
    assert "`;buyability pierce`" in entries[ability_heading(ABILITIES["pierce"])]


def test_the_rules_cover_every_ability_and_fit():
    pages = rules_pages()
    for _name, embed in pages:
        _fits_discord(embed)
    listed = [field.name for _name, embed in pages for field in embed.fields]
    assert all(ability_heading(ab) in listed for ab in ABILITIES.values())
    assert any("level 20" in field.value for field in pages[0][1].fields)


def _utility(payload):
    async def fetch_json(url, **kwargs):
        return 200, payload

    return SimpleNamespace(bot=SimpleNamespace(http_client=SimpleNamespace(fetch_json=fetch_json)))


def test_define_gets_a_page_per_part_of_speech():
    senses = [{"definition": "x" * 900} for _ in range(20)]
    meanings = [{"partOfSpeech": "noun", "definitions": senses}, {"partOfSpeech": "verb", "definitions": senses[:1]}]
    error, pages = asyncio.run(Utility._define(_utility([{"meanings": meanings}]), "run"))
    assert error is None
    assert [name for name, _embed in pages] == ["noun", "verb"]
    assert pages[1][1].description.startswith("**verb**\n1. x")
    for _name, embed in pages:
        _fits_discord(embed)


def test_define_with_no_meanings_says_so():
    error, pages = asyncio.run(Utility._define(_utility([{"meanings": []}]), "zzz"))
    assert "No definition" in error and pages is None


def test_urban_gets_a_page_per_definition():
    entries = [{"definition": f"[word] {i} " + "x" * 5000, "example": "y" * 5000} for i in range(7)]
    error, pages = asyncio.run(Utility._urban(_utility({"list": entries}), "word"))
    assert error is None
    assert len(pages) == 5
    assert pages[0][1].description.startswith("word 0")
    for _name, embed in pages:
        _fits_discord(embed)


def test_win_counting_games_say_wins_and_best_scores_stay_bare():
    from bot.services.scores import score_text

    assert score_text("bombparty", 77) == "77 wins"
    assert score_text("connect4", 1) == "1 win"
    assert score_text("tictactoe", 1500) == "1,500 wins"
    assert score_text("flagle", 1200) == "1,200"


def test_the_profile_only_lists_games_you_played():
    scores = SimpleNamespace(
        user_score=lambda _, game: 1200 if game == "flagle" else None,
        rank=lambda game, score: 3456,
    )
    bot = SimpleNamespace(
        award_achievements=lambda *_: [],
        scores=scores,
        economy=SimpleNamespace(
            equipped_title=lambda _: None,
            balance=lambda _: (10, 2),
            owns=lambda *_: False,
            earned_achievements=lambda _: [],
        ),
        duel=SimpleNamespace(get_or_create=lambda *_: {"level": 1, "xp": 5, "rating": 1000, "wins": 0, "losses": 0}),
    )
    user = SimpleNamespace(id=1, display_avatar=SimpleNamespace(url="https://example.com/a.png"))
    embed = Utility._profile(SimpleNamespace(bot=bot), user)
    _fits_discord(embed)
    games = next(field.value for field in embed.fields if field.name == "🎮 Game scores")
    assert games == "**Flagle**: 1,200 · rank #3,456"
    bot.scores.user_score = lambda *_: None
    embed = Utility._profile(SimpleNamespace(bot=bot), user)
    assert "`;help`" in next(field.value for field in embed.fields if field.name == "🎮 Game scores")


def _economy(earned=(), owned=(), equipped=None, held=False):
    economy = SimpleNamespace(
        earned_achievements=lambda _: list(earned),
        owned_titles=lambda _: list(owned),
        equipped_title=lambda _: equipped,
        owns=lambda *_: held,
        balance=lambda _: (5000, 0),
    )
    return SimpleNamespace(bot=SimpleNamespace(economy=economy, award_achievements=lambda *_: []))


def test_achievements_split_what_you_have_from_what_is_left():
    member = SimpleNamespace(id=1)
    embed = Economy._achievements_embed(_economy(earned=["rich"]), member)
    _fits_discord(embed)
    assert embed.title == f"🏅 Achievements (1/{len(ACHIEVEMENTS)})"
    earned, left = embed.description.split("\n\n")
    assert earned == "**✅ Earned**\n**Rich**: Hold 1,000 MiniCoins at once."
    assert left.startswith("**🔒 Still to earn**\n")
    assert "**First Blood**: Win your first game. +50" in left
    assert len(left.split("\n")) == len(ACHIEVEMENTS)  # the heading stands in for Rich, so every one is listed once
    fresh = Economy._achievements_embed(_economy(), member)
    assert fresh.description.startswith("**🔒 Still to earn**")  # nothing earned, no empty heading
    _fits_discord(fresh)
    everything = Economy._achievements_embed(_economy(earned=list(ACHIEVEMENTS)), member)
    assert "Still to earn" not in everything.description


def test_the_shop_says_what_to_type_for_each_title():
    embed = Economy._shop_embed(
        _economy(owned=["novice", "grinder", "committed"], equipped="grinder"), SimpleNamespace(id=1)
    )
    _fits_discord(embed)
    fields = {field.name: field.value for field in embed.fields}
    assert "**Novice** · yours · `;buy novice`" in fields["🏷️ Titles"]
    assert "**The Grinder** · ✅ wearing · `;buy none`" in fields["🏷️ Titles"]
    assert "`;buy legend`" in fields["🏷️ Titles"]
    assert fields["🎖️ Earned titles"] == "**The Committed** · yours · `;buy committed`"
    assert "`;buy streakshield`" in fields["🛡️ Streak Shield"]
    fresh = Economy._shop_embed(_economy(held=True), SimpleNamespace(id=1))
    assert [field.name for field in fresh.fields] == ["🏷️ Titles", "🛡️ Streak Shield"]  # nothing earned, no empty shelf
    assert "✅ You hold one" in fresh.fields[1].value


def test_scorecard_tables_drop_the_grid_and_round_the_strike_rate():
    table = _table([("Kohli", 56, 32, 175.0), ("Dhoni", 10, 3, 333.3333)], ["Player", "Runs", "Balls", "SR"])
    assert "+--" not in table and "|" not in table
    assert "333.3" in table and "333.33" not in table
    bowling = _table([("Bumrah", "4.2", 20, 3)], ["Player", "Overs", "Runs", "Wkts"], disable_numparse=[1])
    assert "4.2" in bowling


def test_chunked_splits_without_losing_anything():
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunked([], 2) == []
