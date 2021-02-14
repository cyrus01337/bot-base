import contextlib
import json
import re
import os
import traceback
from functools import wraps
from typing import Callable, Iterable, Union

import discord

from base import errors

MULTIPLE_SPACES = re.compile(r" +")


def clear_screen():
    return os.system("cls" if os.name == "nt" else "clear")


def when_ready():
    def inner(coroutine):
        @wraps(coroutine)
        async def predicate(*args, **kwargs):
            self = args[0]
            bot = getattr(self, "bot", self)

            await bot.wait_until_ready()
            return await coroutine(*args, **kwargs)
        return predicate
    return inner


def strip_multi_space(string: str):
    return MULTIPLE_SPACES.sub("", string)


def codeblock(media: Union[str, Iterable], language: str = "py"):
    if isinstance(media, Iterable) and not isinstance(media, str):
        media = json.dumps(media, indent=4)
    return (f"```{language}\n"
            f"{media}\n"
            f"```")


def format_exception(error: Exception):
    blueprint = traceback.format_exception(
        type(error),
        error,
        error.__traceback__
    )
    return ("").join(blueprint)


# https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/core.py#L1784-L1808
def has_intents(**intents):
    def outer(method: Callable):
        def inner(*args, **kwargs):
            missing = []
            source = args[0]
            bot = getattr(source, "bot", source)

            for attr, value in intents.items():
                intent_exists = getattr(bot.intents, attr, None)

                if not intent_exists:
                    continue
                elif intent_exists is not value:
                    missing.append(attr)

            if missing:
                error = errors.IntentsRequired(*missing)
                bot.dispatch("base_error", error)
            return method(*args, **kwargs)
        return inner
    return outer


async def clear_reactions(message: discord.Message):
    try:
        await message.clear_reactions()
    except discord.Forbidden:
        with contextlib.suppress(discord.HTTPException):
            for reaction in message.reactions:
                await message.remove_reaction(reaction, message.guild.me)
