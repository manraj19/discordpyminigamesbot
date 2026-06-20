"""Fight command."""

import discord
from discord import app_commands
from discord.ext import commands

from bot.core.utils import invalid_opponent
from bot.views.fight import INSTRUCTIONS, FightView

CHALLENGE_GIF = "https://tenor.com/view/cj-sekiro-gif-23480678"
GAME = "fight"


def _instructions_embed():
    return discord.Embed(title="Instructions", description=INSTRUCTIONS, color=discord.Color.red())


class Fight(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _record_win(self, member):
        return self.bot.reward(member, 1, GAME)

    @commands.command()
    @commands.cooldown(1, 40, commands.BucketType.user)
    async def fight(self, ctx, opponent: discord.Member):
        reason = invalid_opponent(opponent, ctx.author, self_message="You can't fight yourself!")
        if reason:
            await ctx.send(reason)
            return

        await ctx.send(f"{opponent.mention}, {ctx.author.mention} has challenged you to a fight!")
        await ctx.send(CHALLENGE_GIF)
        await ctx.send(embed=_instructions_embed())
        view = FightView(ctx.author, opponent, on_win=self._record_win)
        await ctx.send(f"{view.turn.mention}, choose your first move:", view=view)

    @app_commands.command(name="fight", description="Challenge another user to a fight")
    @app_commands.describe(opponent="The member you want to challenge")
    @app_commands.checks.cooldown(1, 40, key=lambda i: i.user.id)
    async def fight_slash(self, interaction: discord.Interaction, opponent: discord.Member):
        reason = invalid_opponent(opponent, interaction.user, self_message="You can't fight yourself!")
        if reason:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        await interaction.response.send_message(
            f"{opponent.mention}, {interaction.user.mention} has challenged you to a fight!"
        )
        await interaction.followup.send(CHALLENGE_GIF)
        await interaction.followup.send(embed=_instructions_embed())
        view = FightView(interaction.user, opponent, on_win=self._record_win)
        await interaction.followup.send(f"{view.turn.mention}, choose your first move:", view=view)


async def setup(bot):
    await bot.add_cog(Fight(bot))
