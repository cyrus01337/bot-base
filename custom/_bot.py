import asyncio
import contextlib
import copy
import os
import sys
from collections import OrderedDict
from collections.abc import Iterable
from pathlib import Path
from typing import Container, Dict, List, Tuple, Union

import aiohttp
import discord
from discord.ext import commands

from base import errors
from base import utils
from base.utils import Flags
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
        self._shutdown = False
        self._exclusions = ["jishaku"]
        self._display = asyncio.Event()
        self._on_ready_tasks: List[asyncio.Task] = []
        self._edit_cache: Dict[int, discord.Message] = OrderedDict()
        self._edit_cache_maximum = kwargs.pop("max_edit_messages", 1000)

        self.home_id: int = kwargs.pop("home", None)
        self.error_log_id: int = kwargs.pop("error_log", None)
        self.autocomplete: bool = kwargs.pop("autocomplete", True)
        self.silent: bool = kwargs.pop("silent", False)
        self.no_flags: bool = kwargs.pop("no_flags", False)
        self.excluded_extensions: Container = kwargs.pop("exclude", [])
        self.mentions: Tuple[str] = None
        self.session = aiohttp.ClientSession()
        self.permissions: discord.Permissions = kwargs.pop(
            "permissions",
            discord.Permissions()
        )

        if not self.no_flags:
            Flags(hide=True,
                  no_underscore=True,
                  no_dm_traceback=True)

        super().__init__(*args, **kwargs)
        self.add_check(self._shutdown_check)

        if self.excluded_extensions:
            self.load_base_extensions(exclude=self.excluded_extensions)

        for coroutine in (self.__core_ainit__, self.__ainit__, self.display):
            task = self.loop.create_task(coroutine())
            task.add_done_callback(self._startup_error)

            self._on_ready_tasks.append(task)
        self.add_check(self._shutdown_check)

    @utils.when_ready()
    async def __core_ainit__(self):
        self.mentions = (f"<@{self.user.id}>", f"<@!{self.user.id}>")

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

    def _resolve_to_base_path(self, path: Path):
        root = Path.cwd()
        return path.relative_to(root)

    async def _shutdown_check(self, ctx):
        if self._shutdown:
            return await self.is_owner(ctx.author)
        return True

    async def _autocomplete_command(self, message):
        if self.autocomplete:
            prefixes = await self.get_prefix(message)
            prefix_iterable = (isinstance(prefixes, Iterable) and
                               not isinstance(prefixes, str))

            if prefix_iterable:
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

    async def _process_multi_commands(self, message, payload: List[str]):
        prefix: str = None

        for content in payload:
            if prefix:
                content = f"{prefix}content"

            alt_message = copy.copy(message)
            alt_message.content = content
            ctx = await self.get_context(alt_message)

            if not ctx.valid:
                continue
            if ctx.prefix and not prefix:
                prefix = ctx.prefix
            await self.invoke(ctx)

    def log(self, message):
        if not self.silent:
            print(message)

    def load_extensions(self,
                        path: Union[Path, str], *,
                        exclude: Container[str] = [],
                        recurse: bool = False):
        if isinstance(path, str):
            path = Path(path)
        path = path.resolve()
        glob = path.glob

        if recurse:
            glob = path.rglob

        for file in glob("[!__]*.py"):
            if file.name not in exclude:
                base_path = self._resolve_to_base_path(file)
                resolved = utils.dotted(base_path)
                self.load_extension(resolved)

    def load_base_extensions(self, *, exclude=[]):
        base_path = Path(__file__) / "../../cogs"
        self.load_extensions(base_path, exclude=exclude)

    def trigger_display(self):
        if not self._display.is_set():
            self._display.set()

    async def default_display(self):
        utils.clear_screen()
        print(self.user.name, end="\n\n")

        self.trigger_display()

    async def wait_for_display(self):
        await self._display.wait()

    async def on_startup_error(self, error):
        await self.wait_for_display()
        message = utils.format_exception(error)
        print(message, file=sys.stderr)

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
        split = message.content.split("; ")
        autocompleted = await self._autocomplete_command(message)

        if self.mentions and message.content in self.mentions:
            alt_message = copy.copy(message)
            alt_message.content = f"{message.content} prefix"
            ctx = await self.get_context(alt_message)

            await self.bot.invoke(ctx)
        elif split:
            await self._process_multi_commands(message, split)
        elif not autocompleted:
            await self.process_commands(message)

    async def close(self):
        for task in self._on_ready_tasks:
            task.cancel()

        await self.session.close()
        await super().close()
