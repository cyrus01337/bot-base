import copy
import importlib
import inspect
import os
import sys
from asyncio import Event, Task
from typing import List, Tuple

import aiohttp
import discord
from discord.ext import commands

import custom
from base import errors
from base import utils
from base.cogs import Template, ALL
from base.typings import overwritable


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("intents", discord.Intents.all())
        kwargs.setdefault("command_prefix", commands.when_mentioned())
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

        self._on_ready_tasks: List[Task] = []
        self._display = Event()
        self.home_id: int = kwargs.pop("home", None)
        self.error_log_id: int = kwargs.pop("error_log", None)
        self.mentions: Tuple[str] = None
        self.session = aiohttp.ClientSession()
        self.permissions: discord.Permissions = kwargs.pop(
            "permissions",
            discord.Permissions()
        )

        super().__init__(*args, **kwargs)
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
        match_found = None

        for prefix in prefixes:
            if content.startswith(prefix):
                # in the instance of having multiple, simiar prefixes,
                # this grabs both a prefix serving as the initial match
                # and the longest possible prefix able to be matched
                if not match_found or len(prefix) > len(match_found):
                    match_found = prefix

        if match_found:
            return content[len(match_found):]
        raise ValueError(f'prefix cannot be stripped from "{content}"')

    def _get_cogs(self, path: str):
        ret = ["jishaku"]

        for file in os.listdir(path):
            if file.startswith("__") is False and file.endswith(".py"):
                resolved_path = utils.resolve_path(os.path.join(path, file))
                ret.append(resolved_path)
        return ret

    def _get_inherited_cog(self, cog: Template):
        for template_cog in ALL:
            if isinstance(cog, template_cog):
                return template_cog
        return None

    def _unload_inherited_cog(self, original: custom.Cog):
        reversed_ = {v: k for k, v in self.bot.cogs}
        key = reversed_.get(original)
        self.bot.cogs.pop(key)

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

    def load_extensions(self, path: str = "base/cogs", silent: bool = False):
        paths = []

        if path != "base/cogs":
            paths.append("base/cogs")
        paths.append(path)

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

                if not silent:
                    print(f"{method} cog: {cog}")

    def trigger_display(self):
        if not self._display.is_set():
            self._display.set()

    async def default_display(self):
        utils.clear_screen()
        print(self.user.name, end="\n\n")

        self.trigger_display()

    async def wait_for_display(self):
        if not self._display.is_set():
            await self._display.wait()

    # https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/bot.py#L659-L661
    # https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/bot.py#L601-L625
    def load_extension(self, name):
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError:
            raise commands.ExtensionNotFound(name)
        except Exception as error:
            raise commands.ExtensionFailed(name, error)
        classes = inspect.getmembers(module, inspect.isclass)

        # can turn into function, naming unsure
        for cls in classes:
            if isinstance(cls, Template):
                original = self._get_inherited_cog(cls)

                if original:
                    self._unload_inherited_cog(original)
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

    @commands.Cog.listener()
    async def on_startup_error(self, error):
        await self.wait_for_display()
        message = utils.format_exception(error)
        print(message, file=sys.stderr)

    async def close(self):
        for task in self._on_ready_tasks:
            task.cancel()

        await self.session.close()
        await super().close()
