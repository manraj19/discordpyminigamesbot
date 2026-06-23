"""Owner-only administrative commands.

Every command in this cog is gated to the bot owner via ``cog_check``, so none
of them appear usable to anyone else. They are prefix-only by design (no slash),
keeping owner tooling out of the public command list.
"""

import datetime

import discord
from discord.ext import commands

from bot.core import config, embeds, emojis
from bot.services.scores import SUPPORTED_GAMES
from bot.views.confirm import ConfirmView


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.id == config.OWNER_ID

    # --- monitoring ---
    @commands.command(aliases=["stats"])
    async def overview(self, ctx):
        """A snapshot of the bot: reach, health, and database totals."""
        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        uptime = datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time

        embed = embeds.branded(title="Bot Overview")
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds):,}")
        embed.add_field(name="Shards", value=str(self.bot.shard_count or 1))
        embed.add_field(name="Members (sum)", value=f"{total_members:,}")
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(name="Uptime", value=str(uptime).split(".")[0])
        embed.add_field(name="Blocked users", value=str(len(self.bot.blocklist.all())))
        embed.add_field(name="Unique players", value=f"{self.bot.scores.unique_users():,}")
        embed.add_field(name="Score entries", value=f"{self.bot.scores.total_entries():,}")
        per_game = "\n".join(f"{g.capitalize()}: {self.bot.scores.count(g)}" for g in SUPPORTED_GAMES)
        embed.add_field(name="Entries by game", value=per_game, inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def givecoins(self, ctx, member: discord.Member, amount: int):
        """Grant (or remove, with a negative amount) coins. For testing the economy."""
        self.bot.economy.add_coins(member.id, str(member), amount)
        coins, _ = self.bot.economy.balance(member.id)
        await ctx.send(f"Gave {amount} MiniCoins to {member.mention}. Their balance is now {coins}.")

    @commands.command()
    async def disable(self, ctx, channel_id: int = None):
        """Disable the bot in a channel. Defaults to the current channel."""
        channel_id = channel_id or ctx.channel.id
        self.bot.channel_lock.disable(channel_id)
        await ctx.send(f"Disabled the bot in <#{channel_id}> (`{channel_id}`). Re-enable with `;enable {channel_id}`.")

    @commands.command()
    async def enable(self, ctx, channel_id: int = None):
        """Re-enable the bot in a channel. Defaults to the current channel."""
        channel_id = channel_id or ctx.channel.id
        self.bot.channel_lock.enable(channel_id)
        await ctx.send(f"Re-enabled the bot in <#{channel_id}> (`{channel_id}`).")

    @commands.command()
    async def disabledchannels(self, ctx):
        """List the channels where the bot is disabled."""
        ids = self.bot.channel_lock.all()
        if not ids:
            await ctx.send("No channels are disabled.")
            return
        await ctx.send("Disabled channels:\n" + "\n".join(f"<#{c}> (`{c}`)" for c in ids))

    @commands.command()
    async def resetseason(self, ctx):
        """Reset the duel season (all ratings and trophies back to default)."""

        async def do_reset(interaction):
            champ = self.bot.duel.reset_season()
            msg = "Season reset. Every duelist's rating and trophies are back to default."
            if champ:
                msg = f"{emojis.TROPHY} Season champion: **{champ[0]}** at {champ[1]} rating!\n" + msg
            await interaction.followup.send(msg)

        view = ConfirmView(ctx.author.id, do_reset)
        view.message = await ctx.send(
            "⚠️ Reset the duel season? This sets every duelist's rating and trophies back to default "
            "and can't be undone.",
            view=view,
        )

    @commands.command()
    async def servers(self, ctx):
        """List the servers the bot is in (largest first)."""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        lines = [f"`{g.id}`  {g.name} ({g.member_count or 0:,} members)" for g in guilds[:15]]
        embed = embeds.branded(title=f"Servers ({len(guilds)})", description="\n".join(lines) or "None.")
        if len(guilds) > 15:
            embed.set_footer(text=f"Showing the 15 largest of {len(guilds)}.")
        await ctx.send(embed=embed)

    @commands.command()
    async def leave(self, ctx, guild_id: int):
        """Make the bot leave a server by ID."""
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            await ctx.send("I'm not in a server with that ID.")
            return
        name = guild.name
        await guild.leave()
        await ctx.send(f"Left **{name}** (`{guild_id}`).")

    # --- blocklist ---
    @commands.command()
    async def ban(self, ctx, user: discord.User, *, reason=None):
        """Block a user from using the bot anywhere."""
        if user.id == config.OWNER_ID:
            await ctx.send("You can't block yourself.")
            return
        self.bot.blocklist.add(user.id, reason)
        suffix = f"\nReason: {reason}" if reason else ""
        await ctx.send(f"🔨 Blocked **{user}** (`{user.id}`) from using the bot.{suffix}")

    @commands.command()
    async def unban(self, ctx, user: discord.User):
        """Remove a user from the blocklist."""
        if not self.bot.blocklist.is_blocked(user.id):
            await ctx.send(f"**{user}** isn't blocked.")
            return
        self.bot.blocklist.remove(user.id)
        await ctx.send(f"✅ Unblocked **{user}** (`{user.id}`).")

    @commands.command(aliases=["bans"])
    async def blocklist(self, ctx):
        """Show every blocked user."""
        entries = self.bot.blocklist.all()
        if not entries:
            await ctx.send("No users are blocked.")
            return
        lines = [f"`{user_id}`" + (f" ({reason})" if reason else "") for user_id, reason in entries]
        await ctx.send(embed=embeds.branded(title=f"Blocked Users ({len(entries)})", description="\n".join(lines)))

    # --- maintenance ---
    @commands.command()
    async def sync(self, ctx):
        """Sync the slash-command tree with Discord."""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Command tree synced ({len(synced)} commands).")

    @commands.command()
    async def reload(self, ctx, extension: str = None):
        """Hot-reload one cog (e.g. `;reload fight`) or all of them."""
        from bot.core.bot import EXTENSIONS

        targets = [f"bot.cogs.{extension}"] if extension else EXTENSIONS
        results = []
        for ext in targets:
            try:
                await self.bot.reload_extension(ext)
                results.append(f"✅ `{ext}`")
            except Exception as exc:  # noqa: BLE001 - report any load error to the owner
                results.append(f"❌ `{ext}`: {exc}")
        await ctx.send("\n".join(results)[:1900])

    @commands.command()
    async def load(self, ctx, extension: str):
        try:
            await self.bot.load_extension(f"bot.cogs.{extension}")
            await ctx.send(f"✅ Loaded `{extension}`.")
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"❌ {exc}")

    @commands.command()
    async def unload(self, ctx, extension: str):
        try:
            await self.bot.unload_extension(f"bot.cogs.{extension}")
            await ctx.send(f"✅ Unloaded `{extension}`.")
        except Exception as exc:  # noqa: BLE001
            await ctx.send(f"❌ {exc}")

    @commands.command()
    async def say(self, ctx, *, message: str):
        """Send a message as the bot in the current channel."""
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        await ctx.send(message)

    @commands.command()
    async def restart(self, ctx):
        """Stop the process. Under systemd (Restart=always) this restarts it."""
        await ctx.send("Restarting the bot.")
        await self.bot.close()


async def setup(bot):
    await bot.add_cog(Admin(bot))
