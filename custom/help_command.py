from collections.abc import Iterable
from typing import Union

from discord.ext import commands

from .embed import Embed, Field


class HelpCommand(commands.HelpCommand):
    MEDIUM = Union[commands.Command, commands.Group]
    DEFAULT_HELP = "\U0000203c `No help message provided.`"

    def pass_dest(method):
        def predicate(self, *args, **kwargs):
            return method(self, self.get_destination(), *args, **kwargs)
        return predicate

    def __init__(self):
        super().__init__(command_attrs={
            "help": "Show command/category_commands information"
        })
        self.command_not_found = self.subcommand_not_found = self._pass
        self.send_error_message = self._apass

    # helper functions
    def _format(self, string, iterable: Iterable):
        return string.join(f"`{v}`" for v in sorted(iterable))

    def _capitalise(self, string: str):
        first = string[0]

        if first.isupper():
            return string
        return first.upper() + string[1:]

    def _get_help(self, command: MEDIUM):
        return self.DEFAULT_HELP if command.help is None else command.help

    def _get_aliases(self, command: MEDIUM):
        return self._format(", ", command.aliases)

    def _sort_mapping(self, mapping):
        mapping.setdefault("Uncategorised", mapping[None])
        del mapping[None]
        return sorted(mapping.items(), key=self.key)

    def key(self, data):
        cog = data[0]
        return getattr(cog, "qualified_name", cog)

    def filter(self, command):
        is_owner = self.context.author.id == self.context.bot.owner_id

        return (is_owner is False and command.hidden is False) or is_owner

    def _pass(self, *_):
        pass

    async def _apass(self, *_):
        pass

    # overridden methods
    def get_command_signature(self, command):
        append = ""

        if command.signature:
            append = f" {command.signature}"
        return f"`{self.clean_prefix}{command.name}{append}`"

    @pass_dest
    async def send_command_help(self, dest, command):
        fields = []
        aliases = self._get_aliases(command)

        if aliases != "":
            fields.append(Field("Aliases", aliases))
        fields.append(Field("Usage", self.get_command_signature(command)))
        embed = Embed(title=self._capitalise(command.name),
                      desc=self._get_help(command),
                      fields=fields)
        await dest.send(embed=embed)

    @pass_dest
    async def send_group_help(self, dest, group):
        fields = []
        aliases = self._get_aliases(group)
        subcommands = self._format(", ", (c.name for c in group.commands))

        if aliases != "":
            fields.append(Field("Aliases", aliases))
        fields.extend((Field("Subcommands", subcommands),
                       Field("Usage", self.get_command_signature(group))))
        embed = Embed(title=self._capitalise(group.name),
                      desc=self._get_help(group),
                      fields=fields)
        await dest.send(embed=embed)

    @pass_dest
    async def send_cog_help(self, dest, cog):
        desc = cog.description
        cog_commands = self._format(", ", (c.name for c in cog.get_commands()))
        fields = Field("Commands", cog_commands)

        if desc is None:
            desc = self.DEFAULT_HELP
        embed = Embed(title=self._capitalise(cog.qualified_name),
                      desc=desc,
                      fields=fields)
        await dest.send(embed=embed)

    @pass_dest
    async def send_bot_help(self, dest, mapping):
        mapping = self._sort_mapping(mapping)
        desc = f"For additional support, do `{self.clean_prefix}invite`"
        fields = []

        for cog, cog_commands in mapping:
            if cog_commands != []:
                category = self._capitalise(cog.qualified_name)
                category_commands = self._format(
                    ", ",
                    map(self._capitalise, (c.name for c in cog_commands))
                )

                fields.append(Field(category, category_commands))
        embed = Embed(title="Help", desc=desc, fields=fields)
        await dest.send(embed=embed)
