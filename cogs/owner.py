from os.path import basename
from urllib.parse import urlparse

import aiofiles
import discord
from discord.ext import commands

from base import custom


class Owner(custom.Cog, hidden=True):
    def __init__(self, bot):
        self.bot = bot

        self.bot.invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=self.bot.permissions
        )

    # overwritten cog methods
    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def cog_before_invoke(self, ctx):
        if ctx.command.name == "close":
            emoji = self.bot.emojis[False]
            await ctx.message.add_reaction(emoji)

    async def cog_after_invoke(self, ctx):
        emoji = self.bot.emojis.get(ctx.command_failed)
        await ctx.message.add_reaction(emoji)

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
