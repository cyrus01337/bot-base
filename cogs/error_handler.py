import sys
import traceback
from typing import Set, Union

import discord
from discord.ext import commands

from base import custom, utils
from base.typings import Destination


class ErrorHandler(custom.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.ignored = {
            commands.CommandNotFound,
            commands.CheckFailure
        }
        self.ignored_commands: Set[str] = set()

        self._original_on_error = self.bot.on_error
        self.bot.on_error = self.on_error

    def cog_unload(self):
        self.bot.on_error = self._original_on_error

    def _is_ignored(self, command_name: str, error: Exception):
        return command_name in self.ignored_commands

    # overwritable
    def before_hook(self,
                    medium: Union[str, Destination],
                    error: Exception):
        if isinstance(medium, str):
            return self._is_ignored(medium, error)
        return True

    # overwritable
    async def get_destination(self,
                              initial: discord.Object,
                              default: discord.TextChannel = None):
        message = getattr(initial, "message", initial)

        if isinstance(message, discord.Message):
            return await self.bot.get_context(message)
        return default

    # overwritable
    def format_exception(self, error: Exception):
        return utils.format_exception(error)

    # overwritable
    async def output(self,
                     destination: Union[commands.Context, discord.TextChannel],
                     error):
        etype = type(error)
        tb = error.__traceback__
        formatted = self.format_exception(etype, error, tb)
        embed = discord.Embed(description=f"```py\n"
                                          f"{formatted}\n"
                                          f"```")

        traceback.print_exception(etype, error, tb, file=sys.stderr)
        try:
            await destination.send(embed=embed)
        except discord.Forbidden:
            pass

    async def on_error(self, event, initial, *args, **kwargs):
        destination = await self.get_destination(initial,
                                                 default=self.bot.error_log)
        error = sys.exc_info()[1]

        if error is not None and not self.before_hook(destination, error):
            await self.output(destination, error)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if not self.before_hook(ctx.command.name, error):
            await self.output(ctx, error)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
