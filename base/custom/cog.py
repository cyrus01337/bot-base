from discord.ext import commands


class Cog(commands.Cog):
    def __new__(cls, *args, **kwargs):
        kwargs.setdefault(
            "command_attrs",
            {
                "hidden": kwargs.get("hidden", False)
            }
        )
        return super().__new__(cls, *args, **kwargs)

    def __init_subclass__(cls, hidden: bool = False):
        cls.hidden = hidden
