import sys
import traceback
from typing import Any
from typing import Union

import discord
from discord.ext import commands

from base import custom


class ErrorHandler(custom.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.ignored = {
            commands.CommandNotFound,
            commands.CheckFailure
        }
        self.ignored_commands = set()

        self._original_on_error = self.bot.on_error
        self.bot.on_error = self.on_error

    def cog_unload(self, ctx):
        self.bot.on_error = self._original_on_error

    def is_ignored(self, command: commands.Command, error: Exception):
        name = getattr(command, "name", command)
        return isinstance(error, self.ignored_commands.get(name, self.ignored))

    def _before_hook(self, messageable, error):
        is_ignored_error = (isinstance(messageable, commands.Context) and
                            self.is_ignored(messageable.command, error))

        if is_ignored_error:
            print(error)
        return is_ignored_error

    async def _get_messageable(self, initial: Any):
        if isinstance(initial, discord.Message):
            return await self.bot.get_context(initial)
        else:
            message_found = getattr(initial, "message", None)

            if message_found and isinstance(message_found, discord.Message):
                return await self.bot.get_context(message_found)
        return self.bot.error_log

    # overwritable
    async def output(self,
                     messageable: Union[commands.Context, discord.TextChannel],
                     error):
        etype = type(error)
        tb = error.__traceback__
        formatted = ("").join(traceback.format_exception(etype, error, tb))
        embed = discord.Embed(description=f"```py\n"
                                          f"{formatted}\n"
                                          f"```")

        traceback.print_exception(etype, error, tb, file=sys.stderr)
        try:
            await messageable.send(embed=embed)
        except discord.Forbidden:
            pass

    async def on_error(self, event, initial, *args, **kwargs):
        messageable = await self._get_messageable(initial)
        error = sys.exc_info()[1]

        if not self._before_hook(messageable, error):
            await self.output(messageable, error)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if not self._before_hook(ctx, error):
            await self.output(ctx, error)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
