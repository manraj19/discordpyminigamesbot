"""Flip through a long output one page at a time."""

import contextlib

import discord


def chunked(items, size):
    """``items`` split into lists of at most ``size``."""
    return [items[i : i + size] for i in range(0, len(items), size)]


class PagedView(discord.ui.View):
    """◀ ▶ buttons that move one person's message through ``pages``, a list of
    ``(name, embed)``. Each button shows the name of the page it leads to, and a
    single page gets no buttons at all."""

    def __init__(self, owner_id, pages):
        super().__init__(timeout=180.0)
        self.owner_id = owner_id
        self.names = [name for name, _embed in pages]
        self.embeds = [embed for _name, embed in pages]
        self.index = 0
        self.message = None
        if len(pages) == 1:
            self.clear_items()
            return
        for number, embed in enumerate(self.embeds, 1):
            page = f"Page {number} of {len(pages)}"
            embed.set_footer(text=f"{page} · {embed.footer.text}" if embed.footer.text else page)
        self._name_buttons()

    def _name_buttons(self):
        self.back.label = f"◀ {self.names[self.index - 1]}"
        self.forward.label = f"{self.names[(self.index + 1) % len(self.names)]} ▶"

    async def _turn(self, interaction, step):
        self.index = (self.index + step) % len(self.embeds)
        self._name_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._turn(interaction, -1)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def forward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._turn(interaction, 1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message(
            "Only the person who ran this can turn the pages. Run the command yourself to get your own.",
            ephemeral=True,
        )
        return False

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.children and self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)

    async def send(self, target, ephemeral=False):
        """Post the first page to a ``ctx`` or an ``interaction``, deferred or not."""
        first = {"embed": self.embeds[0], "view": self}
        if not isinstance(target, discord.Interaction):
            self.message = await target.send(**first)
        elif target.response.is_done():
            self.message = await target.followup.send(**first, ephemeral=ephemeral)
        else:
            await target.response.send_message(**first, ephemeral=ephemeral)
            self.message = await target.original_response()
