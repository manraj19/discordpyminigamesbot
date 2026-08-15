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
    RANK_MAX_GAP,
    aggregate_stats,
    arena_opponent,
    arena_reward,
    can_rank,
    elo_update,
    enhance_cost,
    make_combatant,
    new_duel,
    ranked_k,
)
from bot.services.economy import title_name
from bot.views.duel import DuelChallengeView, DuelView, LoadoutView, add_lines_field, rules_embed

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


class Duel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # A tower run outlasts the command cooldown, so without this a player can
        # have two fights going on the same floor and clear it twice.
        self.in_arena = set()

    # --- shared helpers ---
    def _fighter(self, member, name=None):
        rec = self.bot.duel.get_or_create(member.id, str(member))
        levels = self.bot.duel.gear_levels(member.id)
        stats = aggregate_stats(rec["level"], rec["weapon"], rec["armor"], rec["accessory"], levels)
        return make_combatant(name or member.display_name, stats, rec["loadout"]), rec

    async def _settle(self, channel, players, records, mode, bet, widx):
        if widx is None or widx == "draw":  # no decisive result: AFK timeout or turn-cap draw
            if mode == "casual" and bet:
                for player in players:
                    self.bot.economy.add_coins(player.id, str(player), bet)
            refund = f" The {bet}-MiniCoin wagers were refunded." if (mode == "casual" and bet) else ""
            if widx == "draw":
                await channel.send(f"🤝 The duel hit the turn limit and ended in a draw.{refund}")
            elif refund:
                await channel.send(f"⌛ Duel expired.{refund}")
            return
        winner, loser = players[widx], players[1 - widx]
        if mode == "ranked":
            wr, lr = records[widx]["rating"], records[1 - widx]["rating"]
            new_w, new_l = elo_update(
                wr,
                lr,
                k=ranked_k(records[widx]["ranked_games"]),
                k_loser=ranked_k(records[1 - widx]["ranked_games"]),
            )
            win_level = self.bot.duel.apply_match(
                winner.id, str(winner), True, RANKED_WIN_XP, new_rating=new_w, trophies=RANKED_TROPHIES, ranked=True
            )
            loss_level = self.bot.duel.apply_match(
                loser.id, str(loser), False, RANKED_LOSS_XP, new_rating=new_l, ranked=True
            )
            level_up, bonus = self.bot.apply_level_up(winner.id, str(winner), win_level)
            self.bot.apply_level_up(loser.id, str(loser), loss_level)
            new = self.bot.award_achievements(winner.id, str(winner))
            quests, q_level, q_bonus = self.bot.quest_event(winner.id, str(winner), "duel_win", 1)
            msg = (
                f"{emojis.TROPHY} {winner.mention} wins ranked! Rating **{wr}→{new_w}** "
                f"(+{RANKED_TROPHIES} {emojis.TROPHY}) · {loser.mention} **{lr}→{new_l}**"
            )
            extra = RewardResult(
                coins=bonus + q_bonus, level_up=q_level or level_up, new_achievements=new, quests=quests
            ).line()
            if extra:
                msg += f"\n{extra}"
            await channel.send(msg)
            return
        if bet:
            self.bot.economy.add_coins(winner.id, str(winner), bet * 2)
            note = f"takes the **{bet * 2}**-MiniCoin pot {emojis.COIN}"
        else:
            self.bot.economy.add_coins(winner.id, str(winner), CASUAL_WIN_COINS)
            note = f"earns **{CASUAL_WIN_COINS}** MiniCoins {emojis.COIN}"
        win_level = self.bot.duel.apply_match(winner.id, str(winner), True, CASUAL_WIN_XP)
        loss_level = self.bot.duel.apply_match(loser.id, str(loser), False, CASUAL_LOSS_XP)
        level_up, bonus = self.bot.apply_level_up(winner.id, str(winner), win_level)
        self.bot.apply_level_up(loser.id, str(loser), loss_level)
        new = self.bot.award_achievements(winner.id, str(winner))
        quests, q_level, q_bonus = self.bot.quest_event(winner.id, str(winner), "duel_win", 1)
        msg = f"{emojis.TROPHY} {winner.mention} {note}"
        extra = RewardResult(
            coins=bonus + q_bonus, level_up=q_level or level_up, new_achievements=new, quests=quests
        ).line()
        if extra:
            msg += f"\n{extra}"
        await channel.send(msg)

    async def _begin(self, channel, p0, p1, mode, bet):
        c0, r0 = self._fighter(p0)
        c1, r1 = self._fighter(p1)
        state = new_duel(c0, c1, random.randint(0, 1))  # random first move
        players, records = [p0, p1], [r0, r1]

        async def on_end(widx):
            await self._settle(channel, players, records, mode, bet, widx)

        await channel.send(embed=rules_embed())
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
            if mode == "casual" and bet:
                if not self.bot.economy.spend(challenger.id, bet):
                    await channel.send(f"{challenger.mention} can no longer cover the {bet}-MiniCoin wager.")
                    return
                if not self.bot.economy.spend(opponent.id, bet):
                    self.bot.economy.add_coins(challenger.id, str(challenger), bet)
                    await channel.send(f"{opponent.mention} can't cover the {bet}-MiniCoin wager.")
                    return
            await self._begin(channel, challenger, opponent, mode, bet)

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
            finally:
                self.in_arena.discard(member.id)

        async def settle(widx):
            if widx == 0:
                coins = arena_reward(floor, is_boss)
                self.bot.economy.add_coins(member.id, str(member), coins)
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
                await channel.send(f"🤝 {member.mention} drew with {name} on floor {floor}. Try again, it's free.")
            else:
                loss_level = self.bot.duel.apply_match(member.id, str(member), False, ARENA_LOSS_XP)
                self.bot.apply_level_up(member.id, str(member), loss_level)
                note = f"{left} attempts left today." if left else "That was your last attempt for today."
                await channel.send(f"💀 {name} holds floor {floor} against {member.mention}. {note}")

        try:
            await channel.send(embed=rules_embed())
            boss_tag = " · **BOSS**" if is_boss else ""
            await channel.send(
                f"🗼 **Arena floor {floor}**{boss_tag} · vs {label} · {left} attempts left after this one."
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
            bits = stat_bits or g.get("desc", "")
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
    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def duel(self, ctx, opponent: discord.Member, bet: int = 0):
        reason = invalid_opponent(opponent, ctx.author, self_message="You can't duel yourself!")
        if reason:
            await ctx.send(reason)
            return
        if bet < 0:
            await ctx.send("Bet can't be negative.")
            return
        if bet and self.bot.economy.balance(ctx.author.id)[0] < bet:
            await ctx.send("You don't have enough MiniCoins for that wager.")
            return
        await self._challenge(ctx.channel, ctx.author, opponent, "casual", bet)

    @app_commands.command(name="duel", description="Challenge someone to a casual duel (optionally wager MiniCoins)")
    @app_commands.describe(opponent="Who to duel", bet="MiniCoins to wager (0 = friendly)")
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def duel_slash(self, interaction: discord.Interaction, opponent: discord.Member, bet: int = 0):
        reason = invalid_opponent(opponent, interaction.user, self_message="You can't duel yourself!")
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return
        if bet < 0 or (bet and self.bot.economy.balance(interaction.user.id)[0] < bet):
            await interaction.response.send_message("Invalid or unaffordable wager.", ephemeral=True)
            return
        await interaction.response.send_message(f"{emojis.DUEL} Challenge sent!", ephemeral=True)
        await self._challenge(interaction.channel, interaction.user, opponent, "casual", bet)

    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def ranked(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author, self_message="You can't duel yourself!")
        if reason:
            await ctx.send(reason)
            return
        rc = self.bot.duel.get_or_create(ctx.author.id, str(ctx.author))
        ro = self.bot.duel.get_or_create(opponent.id, str(opponent))
        if not can_rank(rc["rating"], ro["rating"]):
            await ctx.send(f"Your ratings are more than {RANK_MAX_GAP} apart, so only a casual `;duel` is allowed.")
            return
        await self._challenge(ctx.channel, ctx.author, opponent, "ranked", 0)

    @app_commands.command(name="ranked", description="Challenge someone to a ranked duel (ELO, no MiniCoins)")
    @app_commands.describe(opponent="Who to duel")
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def ranked_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user, self_message="You can't duel yourself!")
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return
        rc = self.bot.duel.get_or_create(interaction.user.id, str(interaction.user))
        ro = self.bot.duel.get_or_create(opponent.id, str(opponent))
        if not can_rank(rc["rating"], ro["rating"]):
            await interaction.response.send_message(
                f"Your ratings are more than {RANK_MAX_GAP} apart, so only a casual duel is allowed.", ephemeral=True
            )
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

    # --- management commands (prefix only) ---
    @commands.command()
    async def buygear(self, ctx, item: str):
        item = item.lower()
        if item not in GEAR:
            await ctx.send("No such gear. See `;duelshop`.")
            return
        if self.bot.duel.owns_gear(ctx.author.id, item):
            await ctx.send("You already own that.")
            return
        if not self.bot.economy.spend(ctx.author.id, GEAR[item]["price"]):
            await ctx.send("You can't afford that yet.")
            return
        self.bot.duel.get_or_create(ctx.author.id, str(ctx.author))
        self.bot.duel.grant_gear(ctx.author.id, item)
        await ctx.send(f"Bought **{GEAR[item]['name']}**! Equip it with `;equip {item}`.")

    @commands.command()
    async def buyability(self, ctx, ability: str):
        ability = ability.lower()
        ab = ABILITIES.get(ability)
        if ab is None or ab.price <= 0:
            await ctx.send("No such buyable ability. See `;duelshop`.")
            return
        if self.bot.duel.has_ability(ctx.author.id, ability):
            await ctx.send("Already unlocked.")
            return
        if not self.bot.economy.spend(ctx.author.id, ab.price):
            await ctx.send("You can't afford that yet.")
            return
        self.bot.duel.get_or_create(ctx.author.id, str(ctx.author))
        self.bot.duel.unlock_ability(ctx.author.id, ability)
        await ctx.send(f"Unlocked **{ab.name}**! Add it to your kit with `;loadout`.")

    @commands.command()
    async def enhance(self, ctx, item: str):
        item = item.lower()
        if item not in GEAR:
            await ctx.send("No such gear. See `;duelshop`.")
            return
        if not self.bot.duel.owns_gear(ctx.author.id, item):
            await ctx.send("You don't own that gear. Buy it with `;buygear` first.")
            return
        level = self.bot.duel.gear_level(ctx.author.id, item)
        if level >= ENHANCE_MAX:
            await ctx.send(f"**{GEAR[item]['name']} +{level}** is already fully enhanced.")
            return
        cost = enhance_cost(level)
        if not self.bot.economy.spend(ctx.author.id, cost):
            await ctx.send(f"Enhancing to **+{level + 1}** costs **{cost}** MiniCoins. Earn some more first.")
            return
        new_level = self.bot.duel.enhance_gear(ctx.author.id, item)
        slot = GEAR[item]["slot"]
        per = {"weapon": "+1 attack", "armor": "+1 defense", "accessory": "+4 max HP"}[slot]
        msg = f"🔨 **{GEAR[item]['name']} +{new_level}** ({per} per level)."
        if new_level < ENHANCE_MAX:
            msg += f" Next level costs {enhance_cost(new_level)} {emojis.COIN}."
        new = self.bot.award_achievements(ctx.author.id, str(ctx.author))
        extra = RewardResult(new_achievements=new).line()
        if extra:
            msg += f"\n{extra}"
        await ctx.send(msg)

    @commands.command()
    async def equip(self, ctx, item: str):
        result = self.bot.duel.equip(ctx.author.id, item.lower())
        if result == "equipped":
            await ctx.send(f"Equipped **{GEAR[item.lower()]['name']}**.")
        elif result == "unowned":
            await ctx.send("You don't own that gear. Buy it with `;buygear`.")
        else:
            await ctx.send("No such gear. See `;duelshop`.")

    @commands.command()
    async def loadout(self, ctx):
        rec = self.bot.duel.get_or_create(ctx.author.id, str(ctx.author))
        unlocked = [a for a in self.bot.duel.unlocked_abilities(ctx.author.id) if a in ABILITIES and a != "strike"]
        view = LoadoutView(self.bot.duel, ctx.author, unlocked, rec["loadout"])
        view.message = await ctx.send(embed=view.embed(), view=view)


async def setup(bot):
    await bot.add_cog(Duel(bot))
