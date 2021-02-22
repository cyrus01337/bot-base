import contextlib
import sys
from typing import Optional, Set, Text, Tuple, Union

import discord
from discord.ext import commands

from base import custom, typings, utils
from base.typings import Destination, overwritable


class ErrorHandler(custom.Cog):
    def __init__(self, bot, **kwargs):
        self.bot = bot

        self.ignored_errors: Tuple[Exception] = kwargs.get("errors", (
            commands.CommandNotFound,
            commands.CheckFailure
        ))
        self.ignored_commands: Set[Text] = kwargs.get("commands", set())

        self._original_on_error = self.bot.on_error
        self.bot.on_error = self.on_error

    def cog_unload(self):
        self.bot.on_error = self._original_on_error

    async def _error_base(self, error, *, ctx=None):
        error = getattr(error, "original", error)
        medium = None

        if ctx and ctx.command:
            medium = ctx.command.name

        if not self.before_hook(error, medium):
            await self.output(error, ctx)

    @overwritable
    def before_hook(self,
                    error,
                    medium: Optional[Union[Text, Destination]] = None):
        if isinstance(medium, str):
            if medium in self.ignored_commands:
                return True
        elif isinstance(medium, typings.literal.destination):
            return False
        return isinstance(error, self.ignored_errors)

    @overwritable
    def format_exception(self, error):
        message = utils.format_exception(error)
        return utils.codeblock(message)

    @overwritable
    async def get_destination(self,
                              initial: discord.abc.Snowflake,
                              default: discord.TextChannel = None):
        message = getattr(initial, "message", initial)

        if isinstance(message, discord.Message):
            ctx = await self.bot.get_context(message)

            if ctx and ctx.valid:
                return ctx
            return message.channel
        return default

    @overwritable
    async def output(self,
                     error,
                     destination: Optional[Destination] = None):
        formatted = self.format_exception(error)
        embed = discord.Embed(description=formatted)

        if destination:
            with contextlib.suppress(discord.HTTPException):
                await destination.send(embed=embed)

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
