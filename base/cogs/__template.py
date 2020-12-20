from discord.ext import commands

from bot import custom


class Cog(custom.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_event(self, arg):
        pass

    @commands.command()
    async def command(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Cog(bot))
