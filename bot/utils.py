import os


def resolve_path(path: str):
    data = (
        ("./", ""),
        ("/", "."),
        ("\\", "."),
        (".py", "")
    )

    for substr, repl in data:
        path = path.replace(substr, repl)
    return path


def get_cogs(path: str = "bot/cogs"):
    cogs = ["jishaku"]

    for file in os.listdir(path):
        if file.startswith("__") is False and file.endswith(".py"):
            path = resolve_path(file)
            cogs.append(path)
    return cogs


def clear_screen():
    return os.system("cls" if os.name == "nt" else "clear")


def when_ready(coroutine):
    async def predicate(self, *args, **kwargs):
        bot = getattr(self, "bot", self)

        await bot.wait_until_ready()
        return await coroutine(self, *args, **kwargs)
    return predicate
