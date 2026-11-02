"""Fight command."""

from functools import partial

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import invalid_opponent
from bot.views.fight import INSTRUCTIONS, FightView

CHALLENGE_GIF = "https://tenor.com/view/cj-sekiro-gif-23480678"
GAME = "fight"


def _challenge_text(challenger, opponent):
    return f"{opponent.mention}, {challenger.mention} has challenged you to a fight!\n{CHALLENGE_GIF}"


def _instructions_embed():
    return discord.Embed(title="Instructions", description=INSTRUCTIONS, color=discord.Color.red())


class Fight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _view(self, challenger, opponent):
        return FightView(challenger, opponent, on_win=partial(self.bot.finish_match, GAME, [challenger, opponent]))

    @commands.command()
    @commands.cooldown(1, 40, commands.BucketType.user)
    async def fight(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author, self_message="You can't fight yourself!")
        if reason:
            ctx.command.reset_cooldown(ctx)
            await ctx.send(reason)
            return

        await ctx.send(_challenge_text(ctx.author, opponent), embed=_instructions_embed())
        view = self._view(ctx.author, opponent)
        view.message = await ctx.send(f"{view.turn.mention}, choose your first move:", view=view)

    @app_commands.command(name="fight", description="Challenge another user to a fight")
    @app_commands.describe(opponent="The member you want to challenge")
    @app_commands.checks.cooldown(1, 40, key=lambda i: i.user.id)
    async def fight_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user, self_message="You can't fight yourself!")
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        await interaction.response.send_message(
            _challenge_text(interaction.user, opponent), embed=_instructions_embed()
        )
        view = self._view(interaction.user, opponent)
        view.message = await interaction.followup.send(
            f"{view.turn.mention}, choose your first move:", view=view, wait=True
        )


async def setup(bot):
    await bot.add_cog(Fight(bot))
