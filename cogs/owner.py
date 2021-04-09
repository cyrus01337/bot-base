import contextlib
import copy
from typing import Dict

import discord
from discord.ext import commands, flags

from base import custom


class Owner(custom.Cog, hidden=True):
    def __init__(self, bot, **kwargs):
        self.bot = bot

        self._original_get_context = self.bot.get_context
        self._update_command = (
            "jishaku sh git pull --recurse-submodules=yes; "
            "cd ./base; "
            "git checkout tweaks; "
            "git pull; "
            "cd .."
        )
        self.bot.get_context = self.get_context
        self.invite_url: str = None
        self.reactions: Dict[bool, str] = kwargs.get("reactions", {
            True: "\U0001f44e",
            False: "\U0001f44d"
        })

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        self.invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=self.bot.permissions
        )

    def cog_unload(self):
        self.bot.get_context = self._original_get_context

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def cog_before_invoke(self, ctx):
        if ctx.command.name == "close":
            emoji = self.reactions[False]
            await ctx.message.add_reaction(emoji)

    async def cog_after_invoke(self, ctx):
        emoji = self.reactions.get(ctx.command_failed)
        await ctx.message.add_reaction(emoji)

    async def get_context(self, message, *, cls=custom.Context):
        return await self._original_get_context(message, cls=cls)

    async def _attempt_fetch(self, payload):
        channel_found = self.bot.get_channel(payload.channel_id)

        if not channel_found:
            return None

        with contextlib.suppress(discord.HTTPException):
            return await channel_found.fetch_message(payload.message_id)
        return None

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        message_found = await self._attempt_fetch(payload)

        if message_found:
            await self.bot.process_commands(message_found)

    @commands.command()
    async def invite(self, ctx):
        await ctx.send(self.invite_url, delete_after=3)

    @commands.command()
    async def clear(self, ctx):
        await self.bot.display()

    @flags.add_flag("--no-shutdown", action="store_false")
    @flags.command()
    async def update(self, ctx, **flags):
        alt_message = copy.copy(ctx.message)
        alt_message.content = ctx.prefix + self._update_command
        alt_ctx = await self.bot.get_context(alt_message)

        await self.bot.invoke(alt_ctx)

        if not flags.pop("no_shutdown"):
            await self.bot.close()

    @commands.command()
    async def close(self, ctx):
        await self.bot.close()


def setup(bot):
    bot.add_cog(Owner(bot))
