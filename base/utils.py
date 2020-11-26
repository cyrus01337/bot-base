import os


def get_cogs():
    cogs = ["jishaku"]

    for file in os.listdir("./base/cogs"):
        if file.startswith("__") is False and file.endswith(".py"):
            name = file[:-3]
            cogs.append(name)
    return cogs


def clear_screen():
    return os.system("cls" if os.name == "nt" else "clear")


def when_ready(coroutine):
    async def predicate(self, *args, **kwargs):
        bot = getattr(self, "bot", self)

        await bot.wait_until_ready()
        return await coroutine(self, *args, **kwargs)
    return predicate
