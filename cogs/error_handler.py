import sys
from typing import Optional, Set, Union

import discord
from discord.ext import commands

from base import custom, typings, utils
from base.typings import Destination, overwritable


class ErrorHandler(custom.Template):
    def __init__(self, bot):
        self.bot = bot

        self.ignored_errors = {
            commands.CommandNotFound,
            commands.CheckFailure
        }
        self.ignored_commands: Set[str] = set()

        self._original_on_error = self.bot.on_error
        self.bot.on_error = self.on_error

    def cog_unload(self):
        self.bot.on_error = self._original_on_error

    async def _error_base(self, error, *, ctx=None):
        medium = None
        error = getattr(error, "original", error)

        if ctx:
            medium = ctx.command.name

        if not self.before_hook(error, medium):
            await self.output(error)

    # overwritable
    def before_hook(self,
                    error: Exception,
                    medium: Optional[Union[str, Destination]] = None):
        if isinstance(medium, str):
            if medium in self.ignored_commands:
                return True
        elif isinstance(medium, typings.literal.Destination):
            return False
        return type(error) in self.ignored_errors

    # overwritable
    def format_exception(self, error: Exception):
        message = utils.format_exception(error)
        return utils.codeblock(message)

    # overwritable
    async def get_destination(self,
                              initial: discord.Object,
                              default: discord.TextChannel = None):
        message = getattr(initial, "message", initial)

        if isinstance(message, discord.Message):
            return await self.bot.get_context(message)
        return default

    # overwritable
    async def output(self,
                     error,
                     destination: Optional[Destination] = None):
        formatted = self.format_exception(error)
        embed = discord.Embed(description=formatted)

        print(formatted, file=sys.stderr)
        if destination:
            try:
                await destination.send(embed=embed)
            except discord.Forbidden:
                pass

    @overwritable
    async def on_base_error(self, error: Exception):
        if not self.before_hook(error):
            await self._error_base(error)

    async def on_error(self, event, initial, *args, **kwargs):
        destination = await self.get_destination(initial,
                                                 default=self.bot.error_log)
        error = sys.exc_info()[1]

        if error is not None and not self.before_hook(error, destination):
            await self.output(error, destination)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await self._error_base(error, ctx=ctx)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
