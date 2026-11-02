"""Truth or Dare view: pick truth or dare for the next prompt, or leave it to chance."""

import contextlib
import random

import discord

from bot.data import DARE, TRUTH


def random_question_embed(question_type=None):
    question_type = question_type or random.choice(["truth", "dare"])
    question = random.choice(TRUTH if question_type == "truth" else DARE)
    embed = discord.Embed(title="Truth or Dare", description=question, color=discord.Color.random())
    embed.set_footer(text=f"Type: {question_type.capitalize()}")
    return embed


class NextButton(discord.ui.Button):
    def __init__(self, label, style, question_type):
        super().__init__(label=label, style=style)
        self.question_type = question_type

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()  # before the first await, so a double click posts one prompt
        await interaction.response.edit_message(view=None)
        view = TruthOrDareView()
        view.message = await interaction.followup.send(
            embed=random_question_embed(self.question_type), view=view, wait=True
        )


class TruthOrDareView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.message = None
        self.add_item(NextButton("Truth", discord.ButtonStyle.success, "truth"))
        self.add_item(NextButton("Dare", discord.ButtonStyle.danger, "dare"))
        self.add_item(NextButton("Surprise me", discord.ButtonStyle.primary, None))

    async def on_timeout(self):
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=None)
