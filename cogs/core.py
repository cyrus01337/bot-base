import traceback

import discord
from discord.ext import commands

from converters import Lowered
from converters import TriggerConverter
from enums import Trigger


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.features = {
            "genshin impact": self.genshin_impact_coro
        }
        self.features["genshin"] = self.features["genshin impact"]

        self.bot.loop.create_task(self.__ainit__())

    @property
    def community(self):
        return discord.utils.get(self.bot.home.roles, name="Community")

    @property
    def genshin_impact(self):
        return self.bot.home.get_role(763866942074912779)

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        assigned = 0
        total = 0

        for member in self.bot.home.members:
            if self.community not in member.roles:
                try:
                    await member.add_roles(self.community)
                except discord.Forbidden as e:
                    traceback.print_exception(type(e), e, e.__traceback__)
                else:
                    assigned += 1
                finally:
                    total += 1
        if 0 not in (assigned, total):
            print(f"Assigned community role to {assigned}/{total} members")

    async def genshin_impact_coro(self, ctx, trigger: Trigger):
        if trigger is Trigger.IN:
            if self.genshin_impact not in ctx.author.roles:
                await ctx.author.add_roles(self.genshin_impact)
        else:
            if self.genshin_impact in ctx.author.roles:
                await ctx.author.remove_roles(self.genshin_impact)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await member.add_roles(self.community)

    @commands.command()
    async def opt(self, ctx, trigger: TriggerConverter, *, feature: Lowered):
        feature_found = self.features.get(feature, None)
        message = f'No feature called "{feature}"'

        if feature_found:
            message = f"Opted {trigger.name.lower()}: **{feature.title()}**"
            await feature_found(ctx, trigger)
        await ctx.send(message)


def setup(bot):
    bot.add_cog(Core(bot))
