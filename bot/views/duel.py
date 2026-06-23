"""Duel UI: the combat board, the challenge accept/decline prompt, and the rules
embed. All combat rules live in bot.games.duel; this only renders and routes."""

import discord

from bot.core import emojis
from bot.games.duel import ABILITIES, LOADOUT_SIZE, ai_choose, step

_STYLE = {
    "strike": discord.ButtonStyle.danger,
    "heavy": discord.ButtonStyle.danger,
    "bleed": discord.ButtonStyle.danger,
    "venom": discord.ButtonStyle.danger,
    "concuss": discord.ButtonStyle.danger,
    "drain": discord.ButtonStyle.danger,
    "cripple": discord.ButtonStyle.danger,
    "finisher": discord.ButtonStyle.danger,
    "guard": discord.ButtonStyle.success,
    "mend": discord.ButtonStyle.success,
    "focus": discord.ButtonStyle.secondary,
    "sharpen": discord.ButtonStyle.secondary,
}


def rules_embed():
    embed = discord.Embed(
        title="⚔️ How duels work",
        color=discord.Color.dark_red(),
        description=(
            "Duels are turn-based and **deterministic**, so wins come from your decisions, not luck. Each "
            "fighter has **HP** and **energy** (you regain 1 each turn). Spend energy on abilities and drop "
            "your opponent to 0 HP.\n\n"
            f"**Status effects:** {emojis.BLEED} bleed and {emojis.POISON} poison deal damage at the start of "
            f"your turns · {emojis.SHIELD} shield soaks damage · {emojis.STUN} stun skips your next turn · "
            "🔻 weaken lowers attack · 🔺 sharpen raises it.\n\n"
            "Your kit is **Strike** (always available) plus your loadout. Buy gear and abilities in "
            "`;duelshop`, equip with `;equip`, and set your loadout with `;loadout`."
        ),
    )
    kit = "\n".join(
        f"**{ab.name}** ({'free' if ab.cost == 0 else f'{ab.cost}⚡'}): {ab.desc}" for ab in ABILITIES.values()
    )
    embed.add_field(name="Abilities", value=kit, inline=False)
    return embed


def _status_line(c):
    parts = [f"{emojis.HEALTH} {c.hp}/{c.max_hp}", f"{emojis.ENERGY} {c.energy}/{c.max_energy}"]
    if c.shield:
        parts.append(f"{emojis.SHIELD} {c.shield}")
    effects = []
    if c.bleed:
        effects.append(f"{emojis.BLEED}{c.bleed}")
    if c.poison:
        effects.append(f"{emojis.POISON}{c.poison}")
    if c.stun:
        effects.append(emojis.STUN)
    if c.weaken:
        effects.append(f"🔻{c.weaken}")
    if c.empower:
        effects.append(f"🔺{c.empower}")
    line = "  ".join(parts)
    if effects:
        line += "\n" + " ".join(effects)
    return line


class AbilityButton(discord.ui.Button):
    def __init__(self, ability_id):
        ab = ABILITIES[ability_id]
        label = ab.name if ab.cost == 0 else f"{ab.name} ({ab.cost}⚡)"
        super().__init__(label=label, style=_STYLE.get(ability_id, discord.ButtonStyle.secondary))
        self.ability_id = ability_id

    async def callback(self, interaction: discord.Interaction):
        await self.view.on_button(interaction, self.ability_id)


class DuelView(discord.ui.View):
    def __init__(self, players, state, *, on_end, ai_index=None):
        super().__init__(timeout=180.0)
        self.players = players  # [user0, user1]; one may be an AI placeholder
        self.state = state
        self.on_end = on_end
        self.ai_index = ai_index
        self.message = None
        self.log = []
        self.controllable = {players[i].id for i in range(2) if i != ai_index}

    def render_turn(self):
        self.clear_items()
        actor = self.state.fighters[self.state.active]
        kit = ["strike"] + [a for a in actor.loadout if a != "strike"]
        for ability_id in kit:
            button = AbilityButton(ability_id)
            button.disabled = ABILITIES[ability_id].cost > actor.energy
            self.add_item(button)

    def disable_all(self):
        for item in self.children:
            item.disabled = True

    def embed(self, winner=None):
        f0, f1 = self.state.fighters
        embed = discord.Embed(title="⚔️ Duel", color=discord.Color.dark_red())
        embed.add_field(name=self.players[0].display_name, value=_status_line(f0), inline=True)
        embed.add_field(name=self.players[1].display_name, value=_status_line(f1), inline=True)
        if winner is not None:
            widx = 0 if winner is f0 else 1
            embed.description = f"{emojis.TROPHY} **{self.players[widx].display_name}** wins the duel!"
        else:
            embed.description = f"➡️ {self.players[self.state.active].display_name}'s turn"
        if self.log:
            embed.add_field(name="Combat log", value="\n".join(self.log[-6:]), inline=False)
        return embed

    def _run_ai(self):
        winner = None
        while winner is None and self.state.active == self.ai_index:
            _, log, winner = step(self.state, ai_choose(self.state))
            self.log += log
        return winner

    async def on_button(self, interaction, ability_id):
        state = self.state
        if interaction.user.id != self.players[state.active].id:
            msg = "It's not your turn!" if interaction.user.id in self.controllable else "This isn't your duel!"
            await interaction.response.send_message(msg, ephemeral=True)
            return
        if ABILITIES[ability_id].cost > state.fighters[state.active].energy:
            await interaction.response.send_message("Not enough energy for that move.", ephemeral=True)
            return

        _, log, winner = step(state, ability_id)
        self.log += log
        if winner is None and self.ai_index is not None:
            winner = self._run_ai()

        if winner is not None:
            self.disable_all()
            await interaction.response.edit_message(embed=self.embed(winner), view=self)
            self.stop()
            await self.on_end(0 if winner is state.fighters[0] else 1)
            return

        self.render_turn()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in self.controllable

    async def on_timeout(self):
        self.disable_all()
        if self.message:
            try:
                await self.message.edit(content="⌛ The duel timed out.", view=self)
            except discord.HTTPException:
                pass
        await self.on_end(None)


class DuelChallengeView(discord.ui.View):
    """An Accept/Decline prompt shown to the challenged player before a duel."""

    def __init__(self, challenger, opponent, on_accept):
        super().__init__(timeout=60.0)
        self.challenger = challenger
        self.opponent = opponent
        self.on_accept = on_accept
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.opponent.id:
            return True
        await interaction.response.send_message("This challenge isn't for you.", ephemeral=True)
        return False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all()
        self.stop()
        await interaction.response.edit_message(content="✅ Challenge accepted!", view=self)
        await self.on_accept(interaction)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all()
        self.stop()
        await interaction.response.edit_message(content="❌ Challenge declined.", view=self)

    def disable_all(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        self.disable_all()
        if self.message:
            try:
                await self.message.edit(content="⌛ The duel challenge expired.", view=self)
            except discord.HTTPException:
                pass


class LoadoutSelect(discord.ui.Select):
    def __init__(self, unlocked, current):
        options = [
            discord.SelectOption(
                label=ABILITIES[a].name, value=a, description=ABILITIES[a].desc[:100], default=a in current
            )
            for a in unlocked
        ]
        super().__init__(
            placeholder="Pick up to 4 abilities for your loadout",
            min_values=0,
            max_values=min(LOADOUT_SIZE, len(options)),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await self.view.apply(interaction, self.values)


class LoadoutView(discord.ui.View):
    """Edit your duel loadout with a dropdown. The current picks come pre-selected,
    so anything you don't touch stays the same."""

    def __init__(self, duel_service, member, unlocked, current):
        super().__init__(timeout=120.0)
        self.duel = duel_service
        self.member = member
        self.unlocked = unlocked  # ability ids the member has unlocked (excludes Strike)
        self.current = list(current)
        self.message = None
        self._render()

    def _render(self):
        self.clear_items()
        self.add_item(LoadoutSelect(self.unlocked, self.current))

    def embed(self):
        equipped = ", ".join(ABILITIES[a].name for a in self.current) or "none"
        available = ", ".join(ABILITIES[a].name for a in self.unlocked if a not in self.current) or "none"
        embed = discord.Embed(
            title="⚔️ Your loadout",
            color=discord.Color.dark_red(),
            description="Pick up to 4 abilities below. **Strike** is always included, and anything you leave "
            "selected stays put.",
        )
        embed.add_field(name="Equipped", value=f"**Strike**, {equipped}", inline=False)
        embed.add_field(name="Available", value=available, inline=False)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.member.id:
            return True
        await interaction.response.send_message("This isn't your loadout.", ephemeral=True)
        return False

    async def apply(self, interaction, chosen):
        self.duel.set_loadout(self.member.id, chosen)
        self.current = list(chosen)
        self._render()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
