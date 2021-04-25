from collections.abc import Iterable

import discord


class Field(object):
    def __init__(self,
                 name: str = "\u200b",
                 value: str = "\u200b",
                 inline: bool = False):
        self._dict = dict(name=name, value=value, inline=inline)
        self.name = name
        self.value = value
        self.inline = inline

        self.keys = self._dict.keys

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        return (
            f"<Field name={repr(self.name)} value={repr(self.value)} "
            f"inline={repr(self.inline)}>"
        )


class Embed(discord.Embed):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", [])
        kwargs.setdefault("color", kwargs.pop("colour", 0x7289DA))

        if kwargs.get("desc"):
            kwargs["description"] = kwargs.pop("desc")
        super().__init__(*args, **kwargs)

        if isinstance(fields, Field):
            fields = [fields]
        self.add_fields(fields)

    def add_fields(self, fields: Iterable[Field]):
        for field in fields:
            self.add_field(**field._dict)
        return self
