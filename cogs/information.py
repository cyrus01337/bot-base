import re

from discord.ext import commands

from base import custom


class Information(custom.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        self.bot = bot
        self.mentions = re.compile(r"<@!?[0-9]+> ")

        self.bot.help_command = custom.HelpCommand()
        self.bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    def _format_prefixes(self, prefixes: tuple):
        ret = []
        added_mention = False

        for prefix in prefixes:
            prefix = f"{prefix}help"

            if not self.mentions.match(prefix):
                prefix = f"`{prefix}`"
            elif not added_mention:
                added_mention = True
            else:
                continue
            print("Added", prefix, added_mention, self.mentions.match(prefix))
            ret.append(prefix)
        return (", ").join(ret)

    # commands
    @commands.command()
    async def prefix(self, ctx):
        """
        Display the prefix(es) that the bot uses
        """
        prefixes = await self.bot.get_prefix(ctx.message)
        formatted = self._format_prefixes(prefixes)

        await ctx.send(f"You can mention me or use any of the following "
                       f"prefixes like so: {formatted}")


def setup(bot):
    bot.add_cog(Information(bot))
