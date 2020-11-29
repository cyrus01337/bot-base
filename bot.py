import discord
from discord.ext import commands

from bot import custom


class Administrator(custom.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(">>>"),
            intents=discord.Intents.default(),
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=">>>help and pings"
            ),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False
            )
        )
        self.home_id = 464446709146320897

        self.load_extensions("./cogs")

    @property
    def home(self):
        return self.get_guild(self.home_id)


def main():
    Administrator().run()


if __name__ == '__main__':
    try:
        main()
    except RuntimeError:
        pass
