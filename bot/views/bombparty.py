"""Bomb Party lobby: an open join window, since this is a free-for-all rather
than a challenge aimed at one opponent."""

import discord

from bot.games.bombparty import MAX_PLAYERS, MIN_PLAYERS, STARTING_LIVES

LOBBY_SECONDS = 30


class LobbyView(discord.ui.View):
    """Collects 2 to 6 players. ``joined`` belongs to the cog, which releases
    everyone's game session when the match ends."""

    def __init__(self, host, joined, bot):
        super().__init__(timeout=LOBBY_SECONDS)
        self.host = host
        self.joined = joined
        self.bot = bot
        self.message = None

    def embed(self):
        roster = "\n".join(f"{i}. {member.display_name}" for i, member in enumerate(self.joined, 1))
        embed = discord.Embed(
            title="💣 Bomb Party",
            description=(
                f"Type a word containing the letters shown before the bomb goes off. Everyone starts with "
                f"**{STARTING_LIVES}** lives and the last one standing wins. Guesses get tidied up as you go, "
                f"so the game stays in one message.\n\n"
                f"Hit **Join** to play. {MAX_PLAYERS} players max, starting in {LOBBY_SECONDS} seconds."
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(name=f"Players ({len(self.joined)}/{MAX_PLAYERS})", value=roster or "Nobody yet")
        return embed

    async def _close(self, interaction):
        self.stop()
        await interaction.response.edit_message(embed=self.embed(), view=None)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if any(member.id == interaction.user.id for member in self.joined):
            await interaction.response.send_message("You're already in this one.", ephemeral=True)
            return
        if len(self.joined) >= MAX_PLAYERS:
            await interaction.response.send_message("This party is full. Catch the next one.", ephemeral=True)
            return
        if not self.bot.begin_session(interaction.user.id):
            await interaction.response.send_message("Finish your current game first.", ephemeral=True)
            return
        self.joined.append(interaction.user)
        if len(self.joined) >= MAX_PLAYERS:
            await self._close(interaction)
            return
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Start now", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.host.id:
            await interaction.response.send_message("Only the host can start it early.", ephemeral=True)
            return
        if len(self.joined) < MIN_PLAYERS:
            await interaction.response.send_message(f"You need at least {MIN_PLAYERS} players.", ephemeral=True)
            return
        await self._close(interaction)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(embed=self.embed(), view=None)
            except discord.HTTPException:
                pass
