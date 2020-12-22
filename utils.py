import re
import os

multiple_spaces = re.compile(r" +")


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


def clear_screen():
    return os.system("cls" if os.name == "nt" else "clear")


def when_ready(coroutine):
    async def predicate(self, *args, **kwargs):
        bot = getattr(self, "bot", self)

        await bot.wait_until_ready()
        return await coroutine(self, *args, **kwargs)
    return predicate


def strip_multi_space(string: str):
    return multiple_spaces.sub("", string)
