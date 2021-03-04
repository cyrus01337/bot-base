import asyncio
import contextlib
import copy
import sys
from collections import OrderedDict
from collections.abc import Iterable
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import aiohttp
import discord
import toml
from discord.ext import commands

from base import errors, utils
from base.typings import overwritable

_ROOT = Path.cwd()


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self._mystbin = None
        self._mystbin_attempted = False
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
        self.delimiter: str = kwargs.pop("delimiter", ";")
        self.config: Dict = self._get_config()
        self.excluded_extensions: List[str] = kwargs.pop("exclude", [])
        self.mentions: Set[str] = None
        self.session = aiohttp.ClientSession()
        self.mention_command: Optional[str] = kwargs.pop(
            "mention_command",
            "prefix"
        )
        self.permissions: discord.Permissions = kwargs.pop(
            "permissions",
            discord.Permissions()
        )

        kwargs.setdefault("intents", discord.Intents.all())
        kwargs.setdefault(
            "allowed_mentions",
            discord.AllowedMentions(everyone=False, roles=False)
        )
        kwargs.setdefault(
            "activity",
            discord.Activity(type=discord.ActivityType.listening, name="pings")
        )
        kwargs.setdefault(
            "command_prefix",
            commands.when_mentioned_or(
                self.config.get("prefix", commands.when_mentioned)
            )
        )

        if not self.no_flags:
            utils.Flags(hide=True,
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
        self.mentions = {f"<@{self.user.id}>", f"<@!{self.user.id}>"}

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
        if not (self._mystbin or self._mystbin_attempted):
            self._mystbin_attempted = True

            with contextlib.suppress(ModuleNotFoundError):
                import mystbin

                self._mystbin = mystbin.Client()
        return self._mystbin

    def _get_config(self):
        config = {}

        with Path("config.toml") as file:
            with contextlib.suppress(TypeError, toml.TomlDecodeError):
                config = toml.load(file)
        return config.get("bot", config)

    def _startup_error(self, future):
        if future.cancelled():
            return
        error = future.exception()

        if error is not None:
            self.dispatch("startup_error", error)

    def _strip_prefix(self, content, prefixes):
        prefixes = filter(content.startswith, prefixes)
        # in the instance of having multiple, simiar prefixes, this
        # grabs both a prefix serving as the initial match and the
        # longest possible prefix able to be matched
        match_found = max(prefixes, key=len)

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
        return path.relative_to(_ROOT)

    def _is_multi(self, content):
        return content.find(self.delimiter) > -1

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

    async def process_multi_commands(self, message: discord.Message):
        ctx = await self.get_context(message)

        if not ctx.valid:
            return
        content = message.content[len(ctx.prefix):]

        for command in map(str.strip, content.split(self.delimiter)):
            alt_message = copy.copy(message)
            alt_message.content = ctx.prefix + command
            alt_ctx = await self.get_context(alt_message)

            if ctx.valid:
                await self.invoke(alt_ctx)

    def log(self, message):
        if not self.silent:
            print(message)

    def load_extensions(self,
                        path: Union[Path, str], *,
                        exclude: List[str] = [],
                        recurse: bool = False):
        path = Path(path)
        resolved = path.resolve()
        glob = resolved.glob

        if recurse:
            glob = resolved.rglob

        for file in glob("[!__]*.py"):
            if file.name not in exclude:
                base_path = self._resolve_to_base_path(file)
                dotted = utils.dotted(base_path)
                self.load_extension(dotted)

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

    async def on_bot_mention(self, message):
        alt_message = copy.copy(message)
        alt_message.content = f"{message.content} {self.mention_command}"
        alt_ctx = await self.get_context(alt_message)

        await self.invoke(alt_ctx)

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
        if token is None:
            file = Path("TOKEN")

            if file.exists():
                with file.open("r") as f:
                    token = str.strip(f.read())
            else:
                raise errors.TokenNotFound(f'{file.resolve()}" not found')
        super().run(token, **kwargs)

    async def on_message(self, message):
        autocompleted = await self._autocomplete_command(message)

        if self.mentions and message.content in self.mentions:
            if not self.mention_command:
                return
            await self.on_bot_mention(message)
        elif self._is_multi(message.content):
            print("hi")
            await self.process_multi_commands(message)
        elif not autocompleted:
            await self.process_commands(message)

    async def close(self):
        for task in self._on_ready_tasks:
            task.cancel()

        await self.session.close()
        await super().close()
