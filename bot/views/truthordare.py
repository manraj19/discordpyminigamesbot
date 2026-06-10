"""Truth or Dare view: a 'Next' button that serves a fresh random prompt."""

import random

import discord

from bot.data import DARE, TRUTH


def random_question_embed():
    question_type = random.choice(["truth", "dare"])
    question = random.choice(TRUTH if question_type == "truth" else DARE)
    embed = discord.Embed(title="Truth or Dare", description=question, color=discord.Color.random())
    embed.set_footer(text=f"Type: {question_type.capitalize()}")
    return embed


class NextButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=random_question_embed(), view=TruthOrDareView())


class TruthOrDareView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.message = None
        self.add_item(NextButton())

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
