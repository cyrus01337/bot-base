import sys
import traceback

import discord
from discord.ext import commands

import custom


class ErrorHandler(custom.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ignored = (
            commands.CommandNotFound,
            commands.CheckFailure
        )
        self.ignored_commands = dict()

        self._original_on_error = self.bot.on_error
        self.bot.on_error = self.on_error

    async def cog_unload(self, ctx):
        self.bot.on_error = self._original_on_error

    def is_ignored(self, command, error):
        name = getattr(command, "name", command)

        return isinstance(
            error,
            self.ignored_commands.get(name, self.ignored)
        )

    async def on_error(self, event, initial, *args, **kwargs):
        ctx = None

        if isinstance(initial, discord.Message):
            ctx = await self.bot.get_context(initial)
        else:
            message_found = getattr(initial, "message")

            if message_found and isinstance(message_found, discord.Message):
                ctx = await self.bot.get_context(message_found)
            else:
                ctx = self.bot.error_log
        await self.output(*sys.exc_info(), ctx=ctx)

    async def output(self, etype, error, tb, *, ctx):
        formatted = ("").join(traceback.format_exception(etype, error, tb))
        embed = discord.Embed(description=f"```py\n"
                              f"{formatted}\n"
                              f"```")

        traceback.print_exception(etype, error, tb)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if self.is_ignored(ctx.command, error):
            print(error)
        else:
            await self.output(type(error), error, error.__traceback__, ctx=ctx)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
