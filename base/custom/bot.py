from asyncio import Event
from collections.abc import Iterable
from json import dumps

import discord
from discord.ext import commands

import utils
from resources import PREFIXES


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

        super().__init__(*args, **kwargs)
        self._display = Event()
        # self.owner_id = 668906205799907348

        for cog in utils.get_cogs():
            method = "[ ] Loaded"

            try:
                if cog != "jishaku":
                    cog = f"cogs.{cog}"
                self.load_extension(cog)
            except commands.ExtensionError as error:
                method = "[x] Failed"

                if isinstance(error, commands.ExtensionFailed):
                    error = error.original
                self.dispatch("startup_error", error)
            finally:
                cog = cog.replace("cogs.", "")
                print(f"{method} cog: {cog}")
        self._wrap_coroutines(self.__ainit__, self.display)

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
        for prefix in prefixes:
            if content.startswith(prefix):
                return content[len(prefix):]
        raise ValueError(f'prefix cannot be stripped from "{content}"')

    async def _autocomplete_command(self, message):
        prefixes = tuple(self.command_prefix(self, message))

        if message.content.startswith(prefixes):
            name = self._strip_prefix(message.content, prefixes)

            if name != "":
                command_found = self.get_command(name)

                if command_found:
                    ctx = await self.get_context(message)
                    await self.invoke(ctx)
                    return True
                else:
                    for command in self.commands:
                        command_names = (
                            command.name.lower(),
                            *command.aliases
                        )

                        for command_name in command_names:
                            autocompleted = (command_name == name
                                             or command_name.startswith(name))

                            if autocompleted:
                                message.content = message.content.replace(
                                    name,
                                    command_name
                                )
                                ctx = await self.get_context(message)

                                print(f'Autocompleted to "{command.name}"')
                                await self.invoke(ctx)
                                return True
        return False

    # overwritable
    async def __ainit__(self):
        pass

    def handle_display(self):
        if not self._display.is_set():
            self._display.set()

    async def wait_for_display(self):
        if not self._display.is_set():
            await self._display.wait()

    @utils.when_ready
    async def display(self):
        utils.clear_screen()
        print(self.user.name, end="\n\n")

        self.handle_display()

    @commands.Cog.listener()
    async def on_startup_error(self, error):
        await self.wait_for_display()
        raise error

    # overwritten methods
    async def on_message(self, message):
        autocompleted = await self._autocomplete_command(message)

        if not autocompleted:
            await self.process_commands(message)

    def run(self, *args, **kwargs):
        with open("./resources/TOKEN", "r") as f:
            token = str.strip(f.read())
        super().run(token, *args, **kwargs)
