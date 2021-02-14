import asyncio
import contextlib
import copy
import os
from collections import OrderedDict
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Tuple

import aiohttp
import discord
from discord.ext import commands

from .cog import Cog
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

        self._mystbin = None
        self._on_ready_tasks: List[asyncio.Task] = []
        self._exclusions = ["jishaku"]
        self._edit_cache: Dict[int, discord.Message] = OrderedDict()
        self._display = asyncio.Event()
        self._edit_cache_maximum = kwargs.pop("max_edit_messages", 1000)

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

    @property
    def mystbin(self):
        if not self._mystbin:
            with contextlib.suppress(ModuleNotFoundError):
                import mystbin

                self._mystbin = mystbin.Client()
        return self._mystbin

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

    def _get_edit_cached_message(self, message_id: int):
        message_found = self._edit_cache.get(message_id, None)

        if not message_found:
            if len(self._edit_cache) == self._edit_cache_maximum:
                self._edit_cache.popitem(last=False)
        return message_found

    async def _autocomplete_command(self, message):
        prefixes = await self.get_prefix(message)

        if isinstance(prefixes, Iterable) and not isinstance(prefixes, str):
            prefixes = tuple(prefixes)

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

    def load_base_extensions(self, *exclusions: str):
        path = Path(__file__).parent / "../cogs"
        resolved = path.resolve()
        repo_name = resolved.parent.name

        for file in resolved.glob("[!__]*.py"):
            if file.name not in exclusions:
                self.load_extension(f"{repo_name}.cogs.{file.name[:-3]}")

    def trigger_display(self):
        if not self._display.is_set():
            self._display.set()

    async def shutdown_check(self, ctx):
        if self.shutdown:
            return await self.is_owner(ctx.author)
        return True

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
        method = "[ ] Loaded"

        try:
            super().load_extension(name)
        except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotFound):
            method = "[-] Skipped"
        except commands.ExtensionError as error:
            method = "[x] Failed"

            if isinstance(error, commands.ExtensionFailed):
                error = error.original
            self.dispatch("startup_error", error)
        self.log(f"{method} cog: {name}")

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
