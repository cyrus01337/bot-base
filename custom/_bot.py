import asyncio
import copy
import importlib
import inspect
import operator
import os
# import sys
from types import ModuleType
from typing import Dict, List, Tuple

import aiohttp
import discord
from discord.ext import commands

from .cog import Cog, Template
from base import errors
from base import utils
from base.typings import overwritable


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("intents", discord.Intents.all())
        kwargs.setdefault("command_prefix", commands.when_mentioned)
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

        self._on_ready_tasks: List[asyncio.Task] = []
        self._exclusions = ["jishaku"]
        self._display = asyncio.Event()
        self.shutdown = False
        self.silent = kwargs.pop("silent", False)
        self.home_id: int = kwargs.pop("home", None)
        self.error_log_id: int = kwargs.pop("error_log", None)
        self.mentions: Tuple[str] = None
        self.base_extensions: Dict[str, ModuleType] = {}
        self.base_cogs: Dict[str, Cog] = {}
        self.session = aiohttp.ClientSession()
        self.permissions: discord.Permissions = kwargs.pop(
            "permissions",
            discord.Permissions()
        )

        super().__init__(*args, **kwargs)
        self.add_check(self.shutdown_check)

        for coroutine in (self.__ainit__, self.display):
            task = self.loop.create_task(coroutine())
            task.add_done_callback(self._startup_error)

            self._on_ready_tasks.append(task)

    @overwritable
    @utils.when_ready()
    async def __ainit__(self):
        pass

    @overwritable
    @utils.when_ready()
    async def display(self):
        await self.default_display()

    @property
    @utils.has_intents(guilds=True)
    def home(self):
        return self.get_guild(self.home_id)

    @property
    @utils.has_intents(guilds=True)
    def error_log(self):
        return self.home.get_channel(self.error_log_id)

    def _startup_error(self, future):
        if future.cancelled():
            return
        error = future.exception()

        if error is not None:
            self.dispatch("startup_error", error)

    def _strip_prefix(self, content, prefixes):
        match_found: str = None
        prefixes = filter(content.startswith, prefixes)

        for prefix in prefixes:
            # in the instance of having multiple, simiar prefixes,
            # this grabs both a prefix serving as the initial match
            # and the longest possible prefix able to be matched
            if not match_found or len(prefix) > len(match_found):
                match_found = prefix

        if match_found:
            return content[len(match_found):]
        raise ValueError(f'prefix cannot be stripped from "{content}"')

    def _get_cogs(self, path: str):
        ret = []

        if path in self._exclusions:
            ret.append(path)
        # elif not os.path.exists(path):
        #     raise error
        else:
            for file in os.listdir(path):
                if file.startswith("__") is False and file.endswith(".py"):
                    joined = os.path.join(path, file)
                    resolved_path = utils.resolve_path(joined)
                    ret.append(resolved_path)
        return ret

    def _get_cog_path(self, cog: commands.Cog):
        for path, extension in self.extensions.items():
            if cog.__class__ in inspect.getmembers(extension):
                return path
        return None

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

    def log(self, message):
        if not self.silent:
            print(message)

    def load_extensions(self,
                        path: str = "base/cogs",
                        jishaku: bool = True):
        paths = ["base/cogs"]

        if path != "base/cogs":
            paths.append(path)
        if jishaku:
            paths.append("jishaku")

        for cog_path in paths:
            for cog in self._get_cogs(cog_path):
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
                self.log(f"{method} cog: {cog}")

    def trigger_display(self):
        if not self._display.is_set():
            self._display.set()

    def shutdown_check(self):
        return not self.bot.shutdown

    async def default_display(self):
        utils.clear_screen()
        print(self.user.name, end="\n\n")

        self.trigger_display()

    async def wait_for_display(self):
        if not self._display.is_set():
            await self._display.wait()

    # https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/bot.py#L656-L661
    # https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/bot.py#L603-L609
    def load_extension(self, name):
        if name in self.extensions:
            raise commands.ExtensionAlreadyLoaded(name)

        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError:
            raise commands.ExtensionNotFound(name)
        except Exception as error:
            raise commands.ExtensionFailed(name, error)

        def predicate(cls):
            return issubclass(cls, commands.Cog)

        classes = map(
            operator.itemgetter(1),
            inspect.getmembers(module, inspect.isclass)
        )
        cog_class = discord.utils.find(predicate, classes)

        if not cog_class:
            print("Returned")
            return
        print("Subclassed:", issubclass(cog_class, Template))
        if issubclass(cog_class, Template):
            for cog in self.cogs.values():
                print(
                    cog_class,
                    cog.__class__,
                    cog_class.__mro__,
                    isinstance(cog, cog_class),
                    issubclass(cog.__class__, Template),
                    issubclass(cog_class, cog.__class__),
                    sep=", ",
                    end="\n\n"
                )
                if issubclass(cog_class, cog.__class__):
                    path = self._get_cog_path(cog)
                    print("Path:", path)

                    if path:
                        self.unload_extension(path)
                        self.log(f'[=] Ejected cog: {cog.qualified_name}')
        super().load_extension(name)

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

    async def on_message(self, message):
        autocompleted = await self._autocomplete_command(message)

        if self.mentions and message.content in self.mentions:
            alt_message = copy(message)
            alt_message.content = f"{message.content} help"
            ctx = await self.get_context(alt_message)

            await self.invoke(ctx)
        elif not autocompleted:
            await self.process_commands(message)

    async def close(self):
        for task in self._on_ready_tasks:
            task.cancel()

        await self.session.close()
        await super().close()
