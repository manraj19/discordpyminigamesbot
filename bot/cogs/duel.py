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
from bot.core.utils import invalid_opponent
from bot.games.duel import (
    ABILITIES,
    GEAR,
    RANK_MAX_GAP,
    aggregate_stats,
    can_rank,
    elo_update,
    make_combatant,
    new_duel,
)
from bot.views.duel import DuelChallengeView, DuelView, LoadoutView, rules_embed

CASUAL_WIN_COINS = 20
CASUAL_WIN_XP = 15
CASUAL_LOSS_XP = 5
RANKED_WIN_XP = 25
RANKED_LOSS_XP = 8
RANKED_TROPHIES = 10
ARENA_WIN_COINS = 30
ARENA_WIN_XP = 20
ARENA_LOSS_XP = 5
ARENA_LOADOUT = ["heavy", "guard", "bleed", "mend"]


class Duel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- shared helpers ---
    def _fighter(self, member, name=None):
        rec = self.bot.duel.get_or_create(member.id, str(member))
        stats = aggregate_stats(rec["level"], rec["weapon"], rec["armor"], rec["accessory"])
        return make_combatant(name or member.display_name, stats, rec["loadout"]), rec

    async def _settle(self, channel, players, records, mode, bet, widx):
        if widx is None:  # timeout / no result
            if mode == "casual" and bet:
                for player in players:
                    self.bot.economy.add_coins(player.id, str(player), bet)
                await channel.send(f"⌛ Duel expired. The {bet}-MiniCoin wagers were refunded.")
            return
        winner, loser = players[widx], players[1 - widx]
        if mode == "ranked":
            wr, lr = records[widx]["rating"], records[1 - widx]["rating"]
            new_w, new_l = elo_update(wr, lr)
            self.bot.duel.apply_match(
                winner.id, str(winner), True, RANKED_WIN_XP, new_rating=new_w, trophies=RANKED_TROPHIES
            )
            self.bot.duel.apply_match(loser.id, str(loser), False, RANKED_LOSS_XP, new_rating=new_l)
            self.bot.award_achievements(winner.id, str(winner))
            await channel.send(
                f"{emojis.TROPHY} {winner.mention} wins ranked! Rating **{wr}→{new_w}** "
                f"(+{RANKED_TROPHIES} {emojis.TROPHY}) · {loser.mention} **{lr}→{new_l}**"
            )
            return
        if bet:
            self.bot.economy.add_coins(winner.id, str(winner), bet * 2)
            note = f"takes the **{bet * 2}**-MiniCoin pot {emojis.COIN}"
        else:
            self.bot.economy.add_coins(winner.id, str(winner), CASUAL_WIN_COINS)
            note = f"earns **{CASUAL_WIN_COINS}** MiniCoins {emojis.COIN}"
        self.bot.duel.apply_match(winner.id, str(winner), True, CASUAL_WIN_XP)
        self.bot.duel.apply_match(loser.id, str(loser), False, CASUAL_LOSS_XP)
        self.bot.award_achievements(winner.id, str(winner))
        await channel.send(f"{emojis.TROPHY} {winner.mention} {note}")

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
        human, rec = self._fighter(member)
        ai_stats = aggregate_stats(rec["level"])
        ai_stats["attack"] += 2  # a little edge so it isn't a pushover
        ai_fighter = make_combatant("🤖 Arena Bot", ai_stats, ARENA_LOADOUT)
        ai_user = SimpleNamespace(display_name="🤖 Arena Bot", id=0)
        state = new_duel(human, ai_fighter, 0)  # human moves first vs the bot

        async def on_end(widx):
            if widx == 0:
                self.bot.economy.add_coins(member.id, str(member), ARENA_WIN_COINS)
                self.bot.duel.apply_match(member.id, str(member), True, ARENA_WIN_XP)
                self.bot.award_achievements(member.id, str(member))
                await channel.send(
                    f"{emojis.TROPHY} {member.mention} cleared the arena! +{ARENA_WIN_COINS} MiniCoins {emojis.COIN}"
                )
            else:
                self.bot.duel.apply_match(member.id, str(member), False, ARENA_LOSS_XP)
                await channel.send(f"💀 The Arena Bot beat {member.mention}. Gear up and try again.")

        await channel.send(embed=rules_embed())
        view = DuelView([member, ai_user], state, on_end=on_end, ai_index=1)
        view.render_turn()
        view.message = await channel.send(embed=view.embed(), view=view)

    # --- embeds ---
    def _duelist_embed(self, member):
        rec = self.bot.duel.get_or_create(member.id, str(member))
        stats = aggregate_stats(rec["level"], rec["weapon"], rec["armor"], rec["accessory"])
        gear = "\n".join(
            f"{slot.capitalize()}: {GEAR[rec[slot]]['name'] if rec[slot] else 'None'}"
            for slot in ("weapon", "armor", "accessory")
        )
        loadout = ", ".join(ABILITIES[a].name for a in rec["loadout"]) or "None"
        embed = discord.Embed(title=f"⚔️ {member.display_name}'s Duelist", color=discord.Color.dark_red())
        embed.add_field(name="Level", value=f"{rec['level']} ({rec['xp']} xp)", inline=True)
        embed.add_field(name="Rating", value=f"{rec['rating']} 📊", inline=True)
        embed.add_field(name="Record", value=f"{rec['wins']}W / {rec['losses']}L", inline=True)
        embed.add_field(name="Trophies", value=f"{rec['trophies']} {emojis.TROPHY}", inline=True)
        embed.add_field(
            name="Stats",
            value=f"{emojis.HEALTH} {stats['max_hp']}  {emojis.ENERGY} {stats['max_energy']}  "
            f"🗡️ {stats['attack']}  {emojis.SHIELD} {stats['defense']}",
            inline=False,
        )
        embed.add_field(name="Gear", value=gear, inline=True)
        embed.add_field(name="Loadout (Strike + …)", value=loadout, inline=True)
        return embed

    def _shop_embed(self, member):
        owned = set(self.bot.duel.owned_gear(member.id))
        unlocked = set(self.bot.duel.unlocked_abilities(member.id))
        gear_lines = []
        for gid, g in GEAR.items():
            stat_bits = " ".join(
                f"+{v} {k.replace('max_', '')}"
                for k, v in g.items()
                if k in ("attack", "defense", "max_hp", "max_energy")
            )
            tag = "✅ owned" if gid in owned else f"{g['price']} {emojis.COIN}"
            gear_lines.append(f"`{gid}` {g['name']} ({g['slot']}) · {stat_bits} · {tag}")
        abil_lines = []
        for aid, ab in ABILITIES.items():
            if ab.price <= 0:
                continue
            tag = "✅ unlocked" if aid in unlocked else f"{ab.price} {emojis.COIN}"
            abil_lines.append(f"`{aid}` {ab.name}: {ab.desc} · {tag}")
        embed = discord.Embed(title="🛒 Duel Shop", color=discord.Color.dark_red())
        embed.add_field(name="Gear · `;buygear <id>` then `;equip <id>`", value="\n".join(gear_lines), inline=False)
        embed.add_field(
            name="Abilities · `;buyability <id>` then `;loadout`", value="\n".join(abil_lines), inline=False
        )
        return embed

    def _rank_embed(self):
        rows = self.bot.duel.top(10)
        if not rows:
            return discord.Embed(
                title="📊 Duel Rankings", description="No duelists yet.", color=discord.Color.dark_red()
            )
        desc = "\n".join(
            f"{i}. {name} · **{rating}** ({wins}W/{losses}L)" for i, (name, rating, wins, losses) in enumerate(rows, 1)
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
