import asyncio
import contextlib
import functools
import json
import re
import os
import traceback
from collections.abc import Container
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Union

import discord

from base import errors

MULTIPLE_SPACES = re.compile(r" +")


def clear_screen():
    return os.system("cls" if os.name == "nt" else "clear")


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


def dotted(path: Union[Path, str]):
    path = Path(path).with_suffix("")
    parts = path.parts

    if path.drive:
        parts = parts[1:]
    return (".").join(parts)


def prioritise(iterable, *, reverse: bool = False, **attrs):
    good = 1
    bad = 2

    if reverse:
        good = 2
        bad = 1

    def key(obj):
        for key, value in attrs.items():
            try:
                attr = getattr(obj, key)
            except AttributeError:
                return bad
            else:
                is_container = isinstance(value, Container)
                if (is_container and attr in value) or attr == value:
                    continue
                return bad
        return good
    return sorted(iterable, key=key)


def when_ready():
    def inner(coroutine):
        @functools.wraps(coroutine)
        async def predicate(*args, **kwargs):
            self = args[0]
            bot = getattr(self, "bot", self)

            await bot.wait_until_ready()
            return await coroutine(*args, **kwargs)
        return predicate
    return inner


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


async def repeat_get(self,
                     obj: Any,
                     key: str,
                     *, not_value: Optional[Any] = None,
                     use_is: bool = False,
                     wait: Union[int, float] = 1,
                     timeout: Union[int, float] = -1):
    waited = 0

    while True:
        try:
            value = getattr(obj, key)
        except AttributeError as error:
            waited += 1

            await asyncio.sleep(wait)

            if timeout != -1 and waited >= timeout:
                raise error
        else:
            if use_is:
                valid = value is not not_value
            else:
                valid = value != not_value

            if not valid:
                continue
            return value


class Flags:
    def __init__(self, *flags: str, **mapping: bool):
        for flag in map(str.lower, flags):
            os.environ[flag] = "True"

        for flag, value in mapping.items():
            flag = flag.upper()

            if flag != "SCOPE_PREFIX":
                flag = f"JISHAKU_{flag}"
            os.environ[flag] = str(value)


prioritize = prioritise
