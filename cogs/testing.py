from discord.ext import commands

from base import custom


class Testing(custom.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.group(hidden=True)
    async def test(self, ctx):
        await ctx.send("Working!")

    @test.command(name="sub", aliases=["subcommand"])
    async def test_sub(self, ctx):
        await ctx.send("Working!")

    @commands.command(name="public")
    async def public_test(self, ctx):
        await ctx.send("Working!")

    @commands.command()
    async def shutdown(self, ctx):
        """
        If the bot ever does some dumb shit then use this
        """
        self.bot.shutdown = True

        await ctx.send(f"{self.bot.user.name} has been locally shutdown")


def setup(bot):
    bot.add_cog(Testing(bot))
