from typing import Union

import discord
from discord.ext import commands


class Literals:
    destination = (commands.Context, discord.TextChannel)


def overwritable(method):
    return method


Destination = Union[Literals.destination]
literals = Literals
