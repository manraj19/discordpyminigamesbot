"""A generic Yes/No confirmation prompt restricted to one user."""

import discord


class ConfirmView(discord.ui.View):
    def __init__(self, owner_id, on_confirm):
        super().__init__(timeout=30.0)
        self.owner_id = owner_id
        self.on_confirm = on_confirm  # async callable(interaction)
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This isn't your prompt.", ephemeral=True)
        return False

    def _disable(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._disable()
        self.stop()
        await interaction.response.edit_message(view=self)
        await self.on_confirm(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._disable()
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=self)

    async def on_timeout(self):
        self._disable()
        if self.message:
            try:
                await self.message.edit(content="Confirmation timed out.", view=self)
            except discord.HTTPException:
                pass
