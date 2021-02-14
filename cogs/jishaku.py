import re

from jishaku.codeblocks import codeblock_converter
from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES, PythonFeature
from jishaku.features.baseclass import Feature

MYSTBIN = re.compile(r"(https://mystb\.in/([A-Z][a-z]+){3}(\.[A-Z]?[a-z]+)?)")


class Jishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    @Feature.Command(parent="jsk", name="py", aliases=["python"])
    async def jsk_python(self, ctx, *, argument):
        if match_found := MYSTBIN.match(argument):
            url = match_found.group()
            response = await self.bot.mystbin.get(url)
            argument = str(response)
        argument = codeblock_converter(argument)
        await PythonFeature.jsk_python.callback(self, ctx, argument=argument)


def setup(bot):
    bot.add_cog(Jishaku(bot=bot))
