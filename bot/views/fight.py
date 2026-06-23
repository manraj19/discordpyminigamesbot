"""Fight view: a turn-based attack/defend duel between two players."""

import random

import discord

from bot.core import emojis

# Clean, directly-embeddable giphy URLs (the share-link "i.giphy.com/media/v1..."
# form carries a tracking blob and often fails to render in an embed).
ACTION_GIFS = {
    "Light Attack": "https://media.giphy.com/media/AT9t5MK37Bzt90r3Wv/giphy.gif",
    "Heavy Attack": "https://media.giphy.com/media/3ohc1292yKn6Z1saGs/giphy.gif",
    "Crash Out": "https://media.giphy.com/media/ixYRj3H9HOzWE/giphy.gif",
    "Dodge Success": "https://media.giphy.com/media/5TSxsJJuSXahO/giphy.gif",
    "Dodge Fail": "https://media.giphy.com/media/kQiVNXM7Uehr82dfcZ/giphy.gif",
    "Parry Success": "https://media.giphy.com/media/QUvYmUKMfoUhuAoyhx/giphy.gif",
    "Parry Fail": "https://media.giphy.com/media/XGP2jgGMR7lEgWnJ50/giphy.gif",
    "Forfeit": "https://media.giphy.com/media/3ohs4kOJi0cKYTz8Hu/giphy.gif",
}
DEFAULT_GIF = "https://media.giphy.com/media/8tYqTxolfDB1tFmQ8L/giphy.gif"

INSTRUCTIONS = (
    "Light attack: 5-15 damage, doesn't miss\n"
    "Heavy attack: 25-30 damage, 20 percent chance of missing\n"
    "Crash Out: 60 damage, 50/50 chance of hitting either user\n"
    "Dodge: 60 percent success rate\n"
    "Parry: 30 percent success rate, does counter-damage if successful"
)


def _gif_for(last_action):
    if "Light Attack" in last_action:
        return ACTION_GIFS["Light Attack"]
    if "Heavy Attack" in last_action:
        return ACTION_GIFS["Heavy Attack"]
    if "Crash Out" in last_action:
        return ACTION_GIFS["Crash Out"]
    if "dodged" in last_action:
        return ACTION_GIFS["Dodge Fail"] if "failed" in last_action else ACTION_GIFS["Dodge Success"]
    if "parried" in last_action:
        return ACTION_GIFS["Parry Fail"] if "failed" in last_action else ACTION_GIFS["Parry Success"]
    if "forfeited" in last_action:
        return ACTION_GIFS["Forfeit"]
    return DEFAULT_GIF


class FirstMoveSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Attack First", description="Choose to attack first"),
            discord.SelectOption(label="Defend First", description="Choose to defend first"),
            discord.SelectOption(label="Forfeit", description="Quit the fight before it starts"),
        ]
        super().__init__(placeholder="Choose your first move...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: FightView = self.view
        if interaction.user != view.turn:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if self.values[0] == "Forfeit":
            embed = discord.Embed(
                title="Game Over",
                description=f"{interaction.user.mention} has forfeited the fight.",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=None)
            view.stop()
            return

        if self.values[0] == "Attack First":
            view.attacker = view.turn
            view.defender = view.user2 if view.turn == view.user1 else view.user1
        else:
            view.defender = view.turn
            view.attacker = view.user2 if view.turn == view.user1 else view.user1

        view.turn = view.attacker
        await view.start_game(interaction)


class FightView(discord.ui.View):
    def __init__(self, user1, user2, *, on_win=None):
        super().__init__(timeout=60.0)
        self.user1 = user1
        self.user2 = user2
        self.on_win = on_win
        self.hp = {user1: 100, user2: 100}
        self.crash_out_used = {user1: False, user2: False}
        self.round = 1
        self.turn = random.choice([user1, user2])
        self.attacker = None
        self.defender = None
        self.last_action = ""
        self.attack_move = None
        self.phase = "attack"
        self.add_item(FirstMoveSelect())

    async def start_game(self, interaction):
        self.clear_items()
        self.add_item(AttackButton())
        self.add_item(HeavyAttackButton())
        self.add_item(CrashOutButton())
        self.add_item(DodgeButton())
        self.add_item(ParryButton())
        self.disable_defense_buttons()
        self.turn = self.attacker
        await self.update_embed(interaction)

    async def update_embed(self, interaction):
        embed = discord.Embed(title="Fight!", description=f"It's {self.turn.mention}'s turn!")
        embed.add_field(name=f"{self.user1.name}'s HP", value=self.hp[self.user1], inline=True)
        embed.add_field(name=f"{self.user2.name}'s HP", value=self.hp[self.user2], inline=True)
        embed.add_field(name="Round", value=self.round, inline=True)
        embed.add_field(name="Last Action", value=self.last_action or "​", inline=False)
        embed.set_image(url=_gif_for(self.last_action))
        await interaction.response.edit_message(embed=embed, view=self)

    async def end_game(self, interaction, winner):
        coins = await self.on_win(winner) if self.on_win else 0
        description = f"{winner.mention} wins!" + (f"  ·  {emojis.COIN} +{coins} MiniCoins" if coins else "")
        embed = discord.Embed(title="Game Over", description=description)
        embed.add_field(name=f"{self.user1.name}'s HP", value=self.hp[self.user1], inline=True)
        embed.add_field(name=f"{self.user2.name}'s HP", value=self.hp[self.user2], inline=True)
        embed.set_image(url=_gif_for(self.last_action))
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def on_timeout(self):
        for user in (self.user1, self.user2):
            try:
                await user.send("The fight has ended due to inactivity.")
            except discord.HTTPException:
                pass
        self.stop()

    async def _finish_if_dead(self, interaction):
        """End the game the moment a player's HP reaches 0."""
        if self.hp[self.user1] <= 0:
            await self.end_game(interaction, self.user2)
            return True
        if self.hp[self.user2] <= 0:
            await self.end_game(interaction, self.user1)
            return True
        return False

    def _advance_attacker(self):
        self.phase = "attack"
        self.attacker, self.defender = self.defender, self.attacker
        self.turn = self.attacker
        self.round += 1
        self.enable_attack_buttons()
        self.disable_defense_buttons()

    async def next_turn(self, interaction, skip_defense=False):
        # 1) A normal attack hands control to the defender first.
        if self.phase == "attack" and not skip_defense:
            self.phase = "defense"
            self.turn = self.defender
            self.enable_defense_buttons()
            self.disable_attack_buttons()
            await self.update_embed(interaction)
            return

        # 2) Crash Out / missed Heavy Attack: damage (if any) lands immediately.
        if self.phase == "attack" and skip_defense:
            damage = self.attack_move.get("damage", 0)
            if self.attack_move.get("self_damage"):
                self.hp[self.attacker] = max(0, self.hp[self.attacker] - damage)
            else:
                self.hp[self.defender] = max(0, self.hp[self.defender] - damage)

        # 3) Otherwise we're resolving a defense (damage already applied).
        # In every damage-dealing path, check for a knockout BEFORE moving on,
        # so the game ends on the killing blow rather than one move later.
        if await self._finish_if_dead(interaction):
            return

        self._advance_attacker()
        await self.update_embed(interaction)

    def enable_attack_buttons(self):
        for item in self.children:
            if isinstance(item, (AttackButton, HeavyAttackButton, CrashOutButton)):
                item.disabled = False

    def disable_attack_buttons(self):
        for item in self.children:
            if isinstance(item, (AttackButton, HeavyAttackButton, CrashOutButton)):
                item.disabled = True

    def enable_defense_buttons(self):
        for item in self.children:
            if isinstance(item, (DodgeButton, ParryButton)):
                item.disabled = False

    def disable_defense_buttons(self):
        for item in self.children:
            if isinstance(item, (DodgeButton, ParryButton)):
                item.disabled = True

    async def process_defense(self, interaction, defense_move):
        if defense_move == "Dodge":
            if random.random() < 0.6:
                self.last_action = f"{interaction.user.mention} dodged the attack from {self.attacker.mention}."
            else:
                damage = self.attack_move["damage"]
                self.hp[interaction.user] = max(0, self.hp[interaction.user] - damage)
                self.last_action = (
                    f"{interaction.user.mention} failed to dodge and took {damage} damage from {self.attacker.mention}."
                )
        elif defense_move == "Parry":
            if random.random() < 0.7:
                damage = self.attack_move["damage"]
                self.hp[interaction.user] = max(0, self.hp[interaction.user] - damage)
                self.last_action = (
                    f"{interaction.user.mention} failed to parry and took {damage} damage from {self.attacker.mention}."
                )
            else:
                damage = self.attack_move["counter_damage"]
                self.hp[self.attacker] = max(0, self.hp[self.attacker] - damage)
                self.last_action = f"{interaction.user.mention} successfully parried and dealt {damage} damage to {self.attacker.mention}."

        await self.next_turn(interaction)


class CrashOutButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Crash Out", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        view: FightView = self.view
        if interaction.user != view.turn or view.phase != "attack":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        if view.crash_out_used[interaction.user]:
            await interaction.response.send_message("You can only use Crash Out once per game!", ephemeral=True)
            return

        view.crash_out_used[interaction.user] = True
        damage = 60
        if random.random() < 0.5:
            view.attack_move = {"damage": damage}
            view.last_action = (
                f"{interaction.user.mention} did a Crash Out and dealt {damage} damage to {view.defender.mention}."
            )
        else:
            view.attack_move = {"damage": damage, "self_damage": True}
            view.last_action = f"{interaction.user.mention} did a Crash Out and dealt {damage} damage to themselves."
        await view.next_turn(interaction, skip_defense=True)


class AttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Light Attack", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        view: FightView = self.view
        if interaction.user != view.turn or view.phase != "attack":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        view.attack_move = {"damage": random.randint(5, 15), "counter_damage": random.randint(5, 15)}
        view.last_action = f"{interaction.user.mention} did a Light Attack."
        await view.next_turn(interaction)


class HeavyAttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Heavy Attack", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        view: FightView = self.view
        if interaction.user != view.turn or view.phase != "attack":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if random.random() < 0.2:
            view.attack_move = {"damage": 0}
            view.last_action = f"{interaction.user.mention} tried a Heavy Attack but missed!"
            await view.next_turn(interaction, skip_defense=True)
        else:
            damage = random.randint(25, 30)
            view.attack_move = {"damage": damage, "counter_damage": random.randint(25, 30)}
            view.last_action = f"{interaction.user.mention} did a Heavy Attack."
            await view.next_turn(interaction)


class DodgeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Dodge", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view: FightView = self.view
        if interaction.user != view.turn or view.phase != "defense":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        await view.process_defense(interaction, "Dodge")


class ParryButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Parry", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        view: FightView = self.view
        if interaction.user != view.turn or view.phase != "defense":
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        await view.process_defense(interaction, "Parry")
