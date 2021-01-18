from discord.ext import commands


# https://github.com/platform-discord/travis-bott/blob/master/utils/customcontext.py#L33-L79
class Context(commands.Context):
    async def send(self, *args, **kwargs):
        is_owner = await self.bot.is_owner(self.author)
        message = self.message

        if is_owner:
            cached = self.bot._get_edit_cached_message(self.message.id)

            if cached:
                if args:
                    kwargs["content"] = args[0]
                await cached.clear_reactions()
                await cached.edit(**kwargs)
                self.bot._edit_cache[self.message.id] = cached
            else:
                message = await super().send(*args, **kwargs)
                self.bot._edit_cache[self.message.id] = message
        return message
