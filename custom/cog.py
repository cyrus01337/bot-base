from abc import ABCMeta

from discord.ext import commands


def _modify_args(args: tuple, kwargs: dict):
    command_attrs = kwargs.get("command_attrs", None)

    if command_attrs:
        command_attrs.setdefault("hidden", kwargs.get("Hidden", False))
    return args, kwargs


class CogMeta(commands.CogMeta, ABCMeta):
    def __call__(cls, *args, **kwargs):
        args, kwargs = _modify_args(args, kwargs)
        obj = cls.__new__(cls, *args, **kwargs)

        for base in cls.__mro__[:-3]:
            base.__init__(obj, *args, **kwargs)
        return obj


class Cog(commands.Cog, metaclass=CogMeta):
    def __init_subclass__(cls, hidden: bool = False):
        cls.hidden = hidden
