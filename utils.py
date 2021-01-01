import re
import os
import traceback

MULTIPLE_SPACES = re.compile(r" +")


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
    return MULTIPLE_SPACES.sub("", string)


def format_exception(error: Exception):
    formatted = ("").join(traceback.format_exception(
        type(error),
        error,
        error.__traceback__
    ))

    return (f"```py\n"
            f"{formatted}\n"
            f"```")
