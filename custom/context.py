import discord
from discord.ext import commands

from base import utils


# https://github.com/platform-discord/travis-bott/blob/master/utils/customcontext.py#L33-L79
class Context(commands.Context):
    async def send(self, *args, **kwargs):
        if self.bot._shutdown and not await self.bot._shutdown_check(ctx=self):
            return print("[S] Bot has been locally shutdown")
        is_owner = await self.bot.is_owner(self.author)
        message = self.message

        if not is_owner:
            return await super().send(*args, **kwargs)
        cached = self.bot._get_edit_cached_message(self.message.id)

        if cached:
            try:
                await utils.clear_reactions(cached)
                await cached.edit(**kwargs)
                self.bot._edit_cache[self.message.id] = cached
            except discord.NotFound:
                del self.bot._edit_cache[self.message.id]
        else:
            message = await super().send(*args, **kwargs)
            self.bot._edit_cache[self.message.id] = message
        return message
