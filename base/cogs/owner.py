import os

import aiohttp
import discord
from discord.ext import commands

from bot import custom


class Owner(custom.Cog, hidden=True):
    def __init__(self, bot):
        self.bot = bot

        self.indent = "  "
        self.thumbs = {
            True: "\U0001f44e",
            False: "\U0001f44d"
        }
        self.permissions = discord.Permissions(administrator=True)

    async def _download(self, url: str):
        async with self.bot.session.get(url) as response:
            if not (os.path.exists("downloads") and os.path.isdir("downloads")):
                os.mkdir("downloads")
            path = os.path.join("downloads", os.path.basename(url))

            with open(path, "wb") as f:
                chunk = await response.content.read(1024)

                while chunk:
                    f.write(chunk)
                    chunk = await response.content.read(1024)

    # overwritten cog methods
    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def cog_before_invoke(self, ctx):
        if ctx.command.name == "close":
            emoji = self.thumbs.get(False)
            await ctx.message.add_reaction(emoji)

    async def cog_after_invoke(self, ctx):
        emoji = self.thumbs.get(ctx.command_failed)

        if ctx.command_failed:
            pass
        await ctx.message.add_reaction(emoji)

    @commands.command(aliases=["dl", "get"])
    async def download(self, ctx, *urls):
        for url in urls:
            print(url, type(url))
            await self._download(url)

    @commands.command()
    async def invite(self, ctx):
        url = discord.utils.oauth_url(self.bot.user.id,
                                      permissions=self.permissions)
        await ctx.send(url, delete_after=3)

    @commands.command()
    async def clear(self, ctx):
        await self.bot.display()

    @commands.command()
    async def close(self, ctx):
        await self.bot.close()


def setup(bot):
    bot.add_cog(Owner(bot))
