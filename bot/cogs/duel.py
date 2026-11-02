"""Duel: a deterministic, technical combat RPG. Casual (optional wager), ranked
(ELO-only, gap-gated), and a PvE arena, plus gear/ability/loadout management.

Combat rules live in bot.games.duel; persistence in bot.services.duel; coins in
the economy service.
"""

import random
from types import SimpleNamespace

import discord
from discord import app_commands
from discord.ext import commands

from bot.core import emojis
from bot.core.rewards import RewardResult
from bot.core.utils import invalid_opponent
from bot.games.duel import (
    ABILITIES,
    ARENA_DAILY_CAP,
    ENHANCE_MAX,
    GEAR,
    HP_LEVEL_CAP,
    RANK_MAX_GAP,
    SECOND_MOVER_ENERGY,
    WAGER_RAKE_PERCENT,
    aggregate_stats,
    arena_opponent,
    arena_reward,
    can_rank,
    elo_update,
    enhance_cost,
    make_combatant,
    new_duel,
    ranked_k,
    wager_prize,
)
from bot.services.economy import title_name
from bot.views.duel import DuelChallengeView, DuelView, LoadoutView, add_lines_field

CASUAL_WIN_COINS = 20
CASUAL_WIN_XP = 15
CASUAL_LOSS_XP = 5
RANKED_WIN_XP = 25
RANKED_LOSS_XP = 8
RANKED_TROPHIES = 10
RANKED_STREAK_FIRE = 3  # ranked win streak that earns a 🔥 on the leaderboard
ARENA_WIN_XP = 20
ARENA_LOSS_XP = 5
ARENA_TITLE_FLOORS = {10: "towerbreaker", 25: "ascendant"}  # floor -> granted title id


def _attempts(count):
    return f"{count} attempt" + ("" if count == 1 else "s")


def _matching(current, options):
    """Autocomplete: up to 25 ``(value, label)`` options with ``current`` in either."""
    current = current.lower()
    matches = (o for o in options if current in o[0] or current in o[1].lower())
    return [app_commands.Choice(name=label, value=value) for value, label in matches][:25]


async def _gear_choices(interaction, current):
    return _matching(current, [(gid, f"{g['name']} ({g['price']} MiniCoins)") for gid, g in GEAR.items()])


async def _owned_gear_choices(interaction, current):
    owned = interaction.client.duel.owned_gear(interaction.user.id)
    return _matching(current, [(gid, GEAR[gid]["name"]) for gid in owned if gid in GEAR])


async def _ability_choices(interaction, current):
    buyable = [(aid, f"{ab.name} ({ab.price} MiniCoins)") for aid, ab in ABILITIES.items() if ab.price]
    return _matching(current, buyable)


class Duel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # A tower run outlasts the command cooldown, so without this a player can
        # have two fights going on the same floor and clear it twice.
        self.in_arena = set()

    # --- shared helpers ---
    def _fighter(self, member, ranked=False):
        rec = self.bot.duel.get_or_create(member.id, str(member))
        levels = self.bot.duel.gear_levels(member.id)
        level = HP_LEVEL_CAP if ranked else rec["level"]  # a level only ever adds HP, so ranked ignores time played
        stats = aggregate_stats(level, rec["weapon"], rec["armor"], rec["accessory"], levels)
        return make_combatant(member.display_name, stats, rec["loadout"]), rec

    def _return_stakes(self, players, bet, stakes):
        """Hand each player's wager back and close their stake. ``stakes`` can be
        shorter than ``players`` when someone couldn't cover the bet."""
        for player, stake in zip(players, stakes, strict=False):
            self.bot.economy.add_coins(player.id, str(player), bet, "wager")
            self.bot.economy.close_stake(stake)

    async def _settle(self, channel, players, mode, bet, widx, stakes):
        if widx == "draw":  # the turn cap hit with nobody ahead
            self._return_stakes(players, bet, stakes)
            note = f" The {bet}-MiniCoin wagers were refunded." if stakes else ""
            await channel.send(f"🤝 The duel hit the turn limit and ended in a draw.{note}")
            return
        winner, loser = players[widx], players[1 - widx]
        if mode == "ranked":
            # Read now, not when the duel began: a match that finished meanwhile would
            # otherwise have its rating change overwritten by this one.
            win_rec, loss_rec = self.bot.duel.get(winner.id), self.bot.duel.get(loser.id)
            wr, lr = win_rec["rating"], loss_rec["rating"]
            new_w, new_l = elo_update(
                wr, lr, k=ranked_k(win_rec["ranked_games"]), k_loser=ranked_k(loss_rec["ranked_games"])
            )
            win_level = self.bot.duel.apply_match(
                winner.id, str(winner), True, RANKED_WIN_XP, new_rating=new_w, trophies=RANKED_TROPHIES, ranked=True
            )
            loss_level = self.bot.duel.apply_match(
                loser.id, str(loser), False, RANKED_LOSS_XP, new_rating=new_l, ranked=True
            )
            msg = (
                f"{emojis.TROPHY} {winner.mention} wins ranked! Rating **{wr}→{new_w}** "
                f"(+{RANKED_TROPHIES} {emojis.TROPHY}) · {loser.mention} **{lr}→{new_l}**"
            )
        else:
            prize = wager_prize(bet) if bet else CASUAL_WIN_COINS
            self.bot.economy.add_coins(winner.id, str(winner), prize, "wager" if bet else "duel")
            for stake in stakes:
                self.bot.economy.close_stake(stake)
            if bet:
                note = f"takes **{prize}** of the {bet * 2}-MiniCoin pot after the {WAGER_RAKE_PERCENT}% house cut"
            else:
                note = f"earns **{prize}** MiniCoins"
            win_level = self.bot.duel.apply_match(winner.id, str(winner), True, CASUAL_WIN_XP)
            loss_level = self.bot.duel.apply_match(loser.id, str(loser), False, CASUAL_LOSS_XP)
            msg = f"{emojis.TROPHY} {winner.mention} {note} {emojis.COIN}"

        level_up, bonus = self.bot.apply_level_up(winner.id, str(winner), win_level)
        self.bot.apply_level_up(loser.id, str(loser), loss_level)
        new = self.bot.award_achievements(winner.id, str(winner))
        quests, q_level, q_bonus = self.bot.quest_event(winner.id, str(winner), "duel_win", 1)
        extra = RewardResult(
            coins=bonus + q_bonus, level_up=q_level or level_up, new_achievements=new, quests=quests
        ).line()
        await channel.send(f"{msg}\n{extra}" if extra else msg)

    async def _begin(self, channel, p0, p1, mode, bet, stakes):
        ranked = mode == "ranked"
        c0, _ = self._fighter(p0, ranked)
        c1, _ = self._fighter(p1, ranked)
        state = new_duel(c0, c1, random.randint(0, 1), SECOND_MOVER_ENERGY)  # random first move
        players = [p0, p1]

        async def on_end(widx):
            await self._settle(channel, players, mode, bet, widx, stakes)
            await self.bot.announce_played(channel, players)

        view = DuelView(players, state, on_end=on_end)
        view.render_turn()
        view.message = await channel.send(embed=view.embed(), view=view)

    async def _challenge(self, channel, challenger, opponent, mode, bet):
        async def on_accept(interaction):
            if mode == "ranked":
                rc = self.bot.duel.get_or_create(challenger.id, str(challenger))
                ro = self.bot.duel.get_or_create(opponent.id, str(opponent))
                if not can_rank(rc["rating"], ro["rating"]):
                    await channel.send(
                        "Ratings are too far apart for a ranked duel right now. Play a casual one instead."
                    )
                    return
            stakes = []
            if mode == "casual" and bet:
                for player in (challenger, opponent):
                    stake = self.bot.economy.stake(player.id, str(player), bet, "wager")
                    if stake is None:
                        self._return_stakes([challenger], bet, stakes)
                        who = "can no longer" if player is challenger else "can't"
                        await channel.send(f"{player.mention} {who} cover the {bet}-MiniCoin wager.")
                        return
                    stakes.append(stake)
            try:
                await self._begin(channel, challenger, opponent, mode, bet, stakes)
            except Exception:  # the board never reached the channel, so nobody can finish this duel
                self._return_stakes([challenger, opponent], bet, stakes)
                raise

        if mode == "ranked":
            label = "a **ranked** duel"
        elif bet:
            label = f"a **{bet}**-MiniCoin wager duel"
        else:
            label = "a casual duel"
        view = DuelChallengeView(challenger, opponent, on_accept)
        view.message = await channel.send(
            f"{emojis.DUEL} {opponent.mention}, {challenger.mention} challenges you to {label}!", view=view
        )

    async def _arena(self, channel, member):
        if member.id in self.in_arena:
            await channel.send("You're already in the arena. Finish that fight first.")
            return
        human, rec = self._fighter(member)
        floor = rec["arena_floor"] + 1  # you always fight the next uncleared floor
        allowed, left = self.bot.duel.use_arena_attempt(member.id, ARENA_DAILY_CAP)
        if not allowed:
            await channel.send(
                f"You're out of arena attempts for today ({ARENA_DAILY_CAP} per day). They refresh at UTC midnight."
            )
            return
        self.in_arena.add(member.id)
        name, ai_stats, kit, is_boss = arena_opponent(floor, rec["level"])
        label = f"🤖 {name}"
        ai_fighter = make_combatant(label, ai_stats, kit)
        ai_user = SimpleNamespace(display_name=label, id=0)
        state = new_duel(human, ai_fighter, 0)  # human moves first vs the bot

        async def on_end(widx):
            try:
                await settle(widx)
                await self.bot.announce_played(channel, [member])
            finally:
                self.in_arena.discard(member.id)

        async def settle(widx):
            left_note = f"{_attempts(left)} left today." if left else "That was your last attempt for today."
            if widx == 0:
                coins = arena_reward(floor, is_boss)
                self.bot.economy.add_coins(member.id, str(member), coins, "arena")
                new_floor = self.bot.duel.advance_arena_floor(member.id)
                win_level = self.bot.duel.apply_match(member.id, str(member), True, ARENA_WIN_XP)
                level_up, bonus = self.bot.apply_level_up(member.id, str(member), win_level)
                title_id = ARENA_TITLE_FLOORS.get(new_floor)
                if title_id:
                    self.bot.economy.grant_title(member.id, str(member), title_id)
                new = self.bot.award_achievements(member.id, str(member))
                quests, q_level, q_bonus = self.bot.quest_event(member.id, str(member), "duel_win", 1)
                what = "felled the boss on" if is_boss else "cleared"
                msg = f"{emojis.TROPHY} {member.mention} {what} floor **{floor}**! Floor {floor + 1} awaits."
                if title_id:
                    msg += f"\n🗼 You earned the title **{title_name(title_id)}**!"
                extra = RewardResult(
                    coins=coins + bonus + q_bonus,
                    xp=ARENA_WIN_XP,
                    level_up=q_level or level_up,
                    new_achievements=new,
                    quests=quests,
                ).line()
                if extra:
                    msg += f"\n{extra}"
                await channel.send(msg)
            elif widx == "draw":
                await channel.send(f"🤝 {member.mention} drew with {name} on floor {floor}. {left_note}")
            else:
                loss_level = self.bot.duel.apply_match(member.id, str(member), False, ARENA_LOSS_XP)
                self.bot.apply_level_up(member.id, str(member), loss_level)
                await channel.send(f"💀 {name} holds floor {floor} against {member.mention}. {left_note}")

        try:
            boss_tag = " · **BOSS**" if is_boss else ""
            await channel.send(
                f"🗼 **Arena floor {floor}**{boss_tag} · vs {label} · {_attempts(left)} left after this one."
            )
            view = DuelView([member, ai_user], state, on_end=on_end, ai_index=1)
            view.render_turn()
            view.message = await channel.send(embed=view.embed(), view=view)
        except Exception:  # never strand the player behind the guard
            self.in_arena.discard(member.id)
            raise

    # --- embeds ---
    @staticmethod
    def _gear_label(item_id, levels):
        """Display name with its enhancement, e.g. ``Warblade +3``."""
        level = levels.get(item_id, 0)
        return GEAR[item_id]["name"] + (f" +{level}" if level else "")

    def _duelist_embed(self, member):
        rec = self.bot.duel.get_or_create(member.id, str(member))
        levels = self.bot.duel.gear_levels(member.id)
        stats = aggregate_stats(rec["level"], rec["weapon"], rec["armor"], rec["accessory"], levels)
        gear = "\n".join(
            f"{slot.capitalize()}: {self._gear_label(rec[slot], levels) if rec[slot] else 'None'}"
            for slot in ("weapon", "armor", "accessory")
        )
        loadout = ", ".join(ABILITIES[a].name for a in rec["loadout"]) or "None"
        embed = discord.Embed(title=f"⚔️ {member.display_name}'s Duelist", color=discord.Color.dark_red())
        embed.add_field(name="Level", value=f"{rec['level']} ({rec['xp']} xp)", inline=True)
        embed.add_field(name="Rating", value=f"{rec['rating']} 📊", inline=True)
        embed.add_field(name="Record", value=f"{rec['wins']}W / {rec['losses']}L", inline=True)
        embed.add_field(name="Trophies", value=f"{rec['trophies']} {emojis.TROPHY}", inline=True)
        embed.add_field(name="Arena", value=f"🗼 Floor {rec['arena_floor']}", inline=True)
        embed.add_field(
            name="Stats",
            value=f"{emojis.HEALTH} {stats['max_hp']}  {emojis.ENERGY} {stats['max_energy']}  "
            f"{emojis.DUEL} {stats['attack']}  {emojis.SHIELD} {stats['defense']}",
            inline=False,
        )
        embed.add_field(name="Gear", value=gear, inline=True)
        embed.add_field(name="Loadout (Strike + …)", value=loadout, inline=True)
        embed.set_footer(text="Overall stats and per-game scores in ;profile")
        return embed

    def _shop_embed(self, member):
        owned = set(self.bot.duel.owned_gear(member.id))
        levels = self.bot.duel.gear_levels(member.id)
        unlocked = set(self.bot.duel.unlocked_abilities(member.id))
        gear_lines = []
        for gid, g in GEAR.items():
            stat_bits = " ".join(
                f"{v:+d} {k.replace('max_', '')}"
                for k, v in g.items()
                if k in ("attack", "defense", "max_hp", "max_energy")
            )
            bits = " · ".join(filter(None, [stat_bits, g.get("desc")]))
            tag = (
                f"✅ owned{f' +{levels[gid]}' if levels.get(gid) else ''}"
                if gid in owned
                else f"{g['price']} {emojis.COIN}"
            )
            gear_lines.append(f"`{gid}` {g['name']} ({g['slot']}) · {bits} · {tag}")
        abil_lines = []
        for aid, ab in ABILITIES.items():
            if ab.price <= 0:
                continue
            tag = "✅ unlocked" if aid in unlocked else f"{ab.price} {emojis.COIN}"
            abil_lines.append(f"`{aid}` {ab.name}: {ab.desc} · {tag}")
        embed = discord.Embed(title="🛒 Duel Shop", color=discord.Color.dark_red())
        add_lines_field(embed, "Gear · `;buygear <id>`, `;equip <id>`, upgrade with `;enhance <id>`", gear_lines)
        add_lines_field(embed, "Abilities · `;buyability <id>` then `;loadout`", abil_lines)
        return embed

    def _rank_embed(self):
        rows = self.bot.duel.top(10)
        if not rows:
            return discord.Embed(
                title="📊 Duel Rankings", description="No duelists yet.", color=discord.Color.dark_red()
            )
        desc = "\n".join(
            f"{i}. {name} · **{rating}** ({wins}W/{losses}L){' 🔥' if streak >= RANKED_STREAK_FIRE else ''}"
            for i, (name, rating, wins, losses, streak) in enumerate(rows, 1)
        )
        return discord.Embed(title="📊 Duel Rankings", description=desc, color=discord.Color.dark_red())

    # --- play commands ---
    def _casual_problem(self, user, opponent, bet):
        """Why this casual duel can't be offered, or None."""
        reason = invalid_opponent(opponent, user, self_message="You can't duel yourself!")
        if reason:
            return reason
        if bet < 0:
            return "Your bet can't be negative."
        if bet and self.bot.economy.balance(user.id)[0] < bet:
            return "You don't have enough MiniCoins for that wager."
        return None

    def _ranked_problem(self, user, opponent):
        """Why this ranked duel can't be offered, or None."""
        reason = invalid_opponent(opponent, user, self_message="You can't duel yourself!")
        if reason:
            return reason
        rc = self.bot.duel.get_or_create(user.id, str(user))
        ro = self.bot.duel.get_or_create(opponent.id, str(opponent))
        if not can_rank(rc["rating"], ro["rating"]):
            return f"Your ratings are more than {RANK_MAX_GAP} apart, so only a casual duel is allowed."
        return None

    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def duel(self, ctx, opponent: discord.Member, bet: int = 0):
        reason = self._casual_problem(ctx.author, opponent, bet)
        if reason:
            ctx.command.reset_cooldown(ctx)
            await ctx.send(reason)
            return
        await self._challenge(ctx.channel, ctx.author, opponent, "casual", bet)

    @app_commands.command(name="duel", description="Challenge someone to a casual duel (optionally wager MiniCoins)")
    @app_commands.describe(opponent="Who to duel", bet="MiniCoins to wager (0 = friendly)")
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def duel_slash(self, interaction: discord.Interaction, opponent: discord.Member, bet: int = 0):
        reason = self._casual_problem(interaction.user, opponent, bet)
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return
        await interaction.response.send_message(f"{emojis.DUEL} Challenge sent!", ephemeral=True)
        await self._challenge(interaction.channel, interaction.user, opponent, "casual", bet)

    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def ranked(self, ctx, opponent: discord.Member):
        reason = self._ranked_problem(ctx.author, opponent)
        if reason:
            ctx.command.reset_cooldown(ctx)
            await ctx.send(reason)
            return
        await self._challenge(ctx.channel, ctx.author, opponent, "ranked", 0)

    @app_commands.command(name="ranked", description="Challenge someone to a ranked duel (ELO, no MiniCoins)")
    @app_commands.describe(opponent="Who to duel")
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def ranked_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = self._ranked_problem(interaction.user, opponent)
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return
        await interaction.response.send_message(f"{emojis.DUEL} Ranked challenge sent!", ephemeral=True)
        await self._challenge(interaction.channel, interaction.user, opponent, "ranked", 0)

    @commands.command(aliases=["pve"])
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def arena(self, ctx):
        await self._arena(ctx.channel, ctx.author)

    @app_commands.command(name="arena", description="Duel a scaling AI in the arena for MiniCoins and XP")
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def arena_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("🤖 Entering the arena!", ephemeral=True)
        await self._arena(interaction.channel, interaction.user)

    # --- info commands ---
    @commands.command()
    async def duelist(self, ctx, member: discord.Member = None):
        await ctx.send(embed=self._duelist_embed(member or ctx.author))

    @app_commands.command(name="duelist", description="View a duelist profile")
    @app_commands.describe(member="Whose duelist to view (defaults to you)")
    async def duelist_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.send_message(embed=self._duelist_embed(member or interaction.user))

    @commands.command()
    async def duelshop(self, ctx):
        await ctx.send(embed=self._shop_embed(ctx.author))

    @app_commands.command(name="duelshop", description="Browse duel gear and abilities")
    async def duelshop_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._shop_embed(interaction.user))

    @commands.command(aliases=["duelboard"])
    async def duelrank(self, ctx):
        await ctx.send(embed=self._rank_embed())

    @app_commands.command(name="duelrank", description="See the duel rating leaderboard")
    async def duelrank_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._rank_embed())

    # --- management commands ---
    def _buy_gear(self, user, item):
        item = item.lower()
        if item not in GEAR:
            return "No such gear. See `;duelshop`."
        if self.bot.duel.owns_gear(user.id, item):
            return "You already own that."
        if not self.bot.economy.spend(user.id, GEAR[item]["price"], "gear"):
            return "You can't afford that yet."
        self.bot.duel.get_or_create(user.id, str(user))
        self.bot.duel.grant_gear(user.id, item)
        return f"Bought **{GEAR[item]['name']}**! Equip it with `;equip {item}`."

    def _buy_ability(self, user, ability):
        ability = ability.lower()
        ab = ABILITIES.get(ability)
        if ab is None or ab.price <= 0:
            return "No such buyable ability. See `;duelshop`."
        if self.bot.duel.has_ability(user.id, ability):
            return "Already unlocked."
        if not self.bot.economy.spend(user.id, ab.price, "ability"):
            return "You can't afford that yet."
        self.bot.duel.get_or_create(user.id, str(user))
        self.bot.duel.unlock_ability(user.id, ability)
        return f"Unlocked **{ab.name}**! Add it to your kit with `;loadout`."

    def _enhance(self, user, item):
        item = item.lower()
        if item not in GEAR:
            return "No such gear. See `;duelshop`."
        if not self.bot.duel.owns_gear(user.id, item):
            return "You don't own that gear. Buy it with `;buygear` first."
        level = self.bot.duel.gear_level(user.id, item)
        if level >= ENHANCE_MAX:
            return f"**{GEAR[item]['name']} +{level}** is already fully enhanced."
        cost = enhance_cost(level)
        if not self.bot.economy.spend(user.id, cost, "enhance"):
            return f"Enhancing to **+{level + 1}** costs **{cost}** MiniCoins. Earn some more first."
        new_level = self.bot.duel.enhance_gear(user.id, item)
        slot = GEAR[item]["slot"]
        per = {"weapon": "+1 attack", "armor": "+1 defense", "accessory": "+4 max HP"}[slot]
        msg = f"🔨 **{GEAR[item]['name']} +{new_level}** ({per} per level)."
        if new_level < ENHANCE_MAX:
            msg += f" Next level costs {enhance_cost(new_level)} {emojis.COIN}."
        extra = RewardResult(new_achievements=self.bot.award_achievements(user.id, str(user))).line()
        return f"{msg}\n{extra}" if extra else msg

    def _equip(self, user, item):
        item = item.lower()
        result = self.bot.duel.equip(user.id, item)
        if result == "equipped":
            return f"Equipped **{GEAR[item]['name']}**."
        if result == "unowned":
            return "You don't own that gear. Buy it with `;buygear`."
        return "No such gear. See `;duelshop`."

    def _loadout_view(self, user):
        rec = self.bot.duel.get_or_create(user.id, str(user))
        unlocked = [a for a in self.bot.duel.unlocked_abilities(user.id) if a in ABILITIES and a != "strike"]
        return LoadoutView(self.bot.duel, user, unlocked, rec["loadout"])

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def buygear(self, ctx, item: str):
        await ctx.send(self._buy_gear(ctx.author, item))

    @app_commands.command(name="buygear", description="Buy a piece of duel gear")
    @app_commands.describe(item="The gear to buy")
    @app_commands.autocomplete(item=_gear_choices)
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def buygear_slash(self, interaction: discord.Interaction, item: str):
        await interaction.response.send_message(self._buy_gear(interaction.user, item))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def buyability(self, ctx, ability: str):
        await ctx.send(self._buy_ability(ctx.author, ability))

    @app_commands.command(name="buyability", description="Unlock a duel ability")
    @app_commands.describe(ability="The ability to unlock")
    @app_commands.autocomplete(ability=_ability_choices)
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def buyability_slash(self, interaction: discord.Interaction, ability: str):
        await interaction.response.send_message(self._buy_ability(interaction.user, ability))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def enhance(self, ctx, item: str):
        await ctx.send(self._enhance(ctx.author, item))

    @app_commands.command(name="enhance", description="Upgrade a piece of gear you own")
    @app_commands.describe(item="The gear to upgrade")
    @app_commands.autocomplete(item=_owned_gear_choices)
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def enhance_slash(self, interaction: discord.Interaction, item: str):
        await interaction.response.send_message(self._enhance(interaction.user, item))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def equip(self, ctx, item: str):
        await ctx.send(self._equip(ctx.author, item))

    @app_commands.command(name="equip", description="Equip a piece of gear you own")
    @app_commands.describe(item="The gear to equip")
    @app_commands.autocomplete(item=_owned_gear_choices)
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def equip_slash(self, interaction: discord.Interaction, item: str):
        await interaction.response.send_message(self._equip(interaction.user, item))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def loadout(self, ctx):
        view = self._loadout_view(ctx.author)
        view.message = await ctx.send(embed=view.embed(), view=view)

    @app_commands.command(name="loadout", description="Pick the abilities you take into a duel")
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def loadout_slash(self, interaction: discord.Interaction):
        view = self._loadout_view(interaction.user)
        await interaction.response.send_message(embed=view.embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(Duel(bot))
