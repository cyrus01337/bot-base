from typing import Union

import discord
from discord.ext import commands


class Literals:
    destination = (commands.Context, discord.TextChannel)


Destination = Union[Literals.destination]
literals = Literals
