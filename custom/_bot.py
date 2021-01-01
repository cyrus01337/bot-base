import copy
import inspect
import os
import sys
import traceback
from asyncio import Event
from collections.abc import Iterable
from json import dumps
from typing import Dict

import aiohttp
import discord
from discord.ext import commands

# from base import cogs
from base import errors
from base import utils
from base.resources import PREFIXES


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("intents", discord.Intents.all())
        kwargs.setdefault(
            "command_prefix",
            commands.when_mentioned_or(*PREFIXES)
        )
        kwargs.setdefault(
            "allowed_mentions",
            discord.AllowedMentions(everyone=False, roles=False)
        )
        kwargs.setdefault(
            "activity",
            discord.Activity(
                type=discord.ActivityType.listening,
                name="pings"
            )
        )

        self._display = Event()
        self.session = aiohttp.ClientSession()
        self.reactions: Dict[bool, str] = kwargs.pop("reactions", {
            True: "\U0001f44e",
            False: "\U0001f44d"
        })
        self.permissions: discord.Permissions = kwargs.pop(
            "permissions",
            discord.Permissions()
        )

        super().__init__(*args, **kwargs)
        self._wrap_coroutines(self.__ainit__, self.display)

    def __init_subclass__(cls):
        ainit = getattr(cls, "__ainit__", None)

        if ainit and inspect.iscoroutinefunction(ainit):
            cls.__ainit__ = utils.when_ready(ainit)

    # overwritable
    @utils.when_ready
    async def __ainit__(self):
        pass

    @property
    def home(self):
        return self.get_guild(464446709146320897)

    @property
    def error_log(self):
        return self.home.get_channel(778758649938051073)

    def _formatted(self, iterable: Iterable, **kwargs):
        # for usage with Jishaku
        kwargs["indent"] = kwargs.get("indent", 4)

        if isinstance(iterable, map):
            iterable = tuple(iterable)
        return (f"```py\n"
                f"{dumps(iterable, **kwargs)}\n"
                f"```")

    def _startup_error(self, future):
        error = future.exception()

        if error is not None:
            self.dispatch("startup_error", error)

    def _wrap_coroutines(self, *coroutines):
        for coroutine in coroutines:
            task = self.loop.create_task(coroutine())
            task.add_done_callback(self._startup_error)

    def _strip_prefix(self, content, prefixes):
        match_found = None

        for prefix in prefixes:
            if content.startswith(prefix):
                # in the instance of having multiple prefixes similar to
                # each other, this grabs both a prefix serving as the
                # initial match and the longest possible prefix able to
                # be matched
                if not match_found or len(prefix) > len(match_found):
                    match_found = prefix

        if match_found:
            return content[len(match_found):]
        raise ValueError(f'prefix cannot be stripped from "{content}"')

    async def _autocomplete_command(self, message):
        prefixes = tuple(self.command_prefix(self, message))

        if message.content.startswith(prefixes):
            name = self._strip_prefix(message.content, prefixes)

            if name != "":
                command_found = self.get_command(name)

                if command_found:
                    ctx = await self.get_context(message)

                    print(f'Autocompleted to "{ctx.command.name}"')
                    await self.invoke(ctx)
                    return command_found
                else:
                    for command in self.commands:
                        command_names = (
                            command.name.lower(),
                            *command.aliases
                        )

                        for command_name in command_names:
                            autocompleted = command_name == name \
                                or command_name.startswith(name)

                            if autocompleted:
                                alt_message = copy.copy(message)
                                alt_content = alt_message.content.replace(
                                    name,
                                    command_name
                                )
                                alt_message.content = alt_content
                                ctx = await self.get_context(alt_message)

                                await self.invoke(ctx)
                                return command
        return None

    def get_cogs(self, path: str):
        ret = ["jishaku"]

        for file in os.listdir(path):
            if file.startswith("__") is False and file.endswith(".py"):
                resolved_path = utils.resolve_path(os.path.join(path, file))
                ret.append(resolved_path)
        return ret

    def load_extensions(self, path: str = "base/cogs", exclude: Iterable = ()):
        paths = []

        if path != "base/cogs":
            paths.append("base/cogs")
        paths.append(path)

        for cog_path in paths:
            for cog in self.get_cogs(cog_path):
                if cog in exclude:
                    continue
                method = "[ ] Loaded"

                try:
                    self.load_extension(cog)
                except commands.ExtensionAlreadyLoaded:
                    continue
                except commands.ExtensionNotFound:
                    method = "[-] Skipped"
                except commands.ExtensionError as error:
                    method = "[x] Failed"

                    if isinstance(error, commands.ExtensionFailed):
                        error = error.original
                    self.dispatch("startup_error", error)
                print(f"{method} cog: {cog}")

    async def wait_for_display(self):
        if not self._display.is_set():
            await self._display.wait()

    @commands.Cog.listener()
    async def on_startup_error(self, error):
        await self.wait_for_display()
        formatted = traceback.format_exception(
            type(error),
            error,
            error.__traceback__
        )
        joined = ("").join(formatted)
        print(joined, file=sys.stderr)

    # overwritable
    def handle_display(self):
        if not self._display.is_set():
            self._display.set()

    # overwritable
    @utils.when_ready
    async def display(self):
        utils.clear_screen()
        print(self.user.name, end="\n\n")

        self.handle_display()

    # overwritten methods
    async def on_message(self, message):
        autocompleted = await self._autocomplete_command(message)

        if not autocompleted:
            await self.process_commands(message)

    def load_extension(self, name):
        return super().load_extension(name)

    def run(self, token=None, **kwargs):
        path = "./TOKEN"

        if token is None:
            if os.path.exists(path):
                with open(path, "r") as f:
                    token = str.strip(f.read())
            else:
                full = os.path.abspath(path)
                raise errors.TokenFileNotFound(f'{full}" not found')
        super().run(token, **kwargs)

    async def close(self):
        await self.session.close()
        await super().close()
