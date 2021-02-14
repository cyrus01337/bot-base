from os.path import basename
from urllib.parse import urlparse
from typing import Dict

import aiofiles
import discord
from discord.ext import commands

from base import custom


class Owner(custom.Cog, hidden=True):
    def __init__(self, bot, **kwargs):
        self.bot = bot

        self._original_get_context = self.bot.get_context
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
        return await channel_found.fetch_message(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        message_found = await self._attempt_fetch(payload)

        if message_found:
            await self.bot.process_commands(message_found)

    @commands.command(aliases=["dl", "get"])
    async def download(self, ctx, *urls):
        for url in urls:
            async with self.bot.session.get(url) as response:
                parsed = urlparse(url)
                filename = basename(parsed.path)

                async with aiofiles.open(f"downloads/{filename}", "wb") as f:
                    chunk = await response.content.read(1024)

                    while chunk:
                        await f.write(chunk)
                        chunk = await response.content.read(1024)

    @commands.command()
    async def invite(self, ctx):
        await ctx.send(self.bot.invite_url, delete_after=3)

    @commands.command()
    async def clear(self, ctx):
        await self.bot.display()

    @commands.command()
    async def close(self, ctx):
        await self.bot.close()


def setup(bot):
    bot.add_cog(Owner(bot))
