import operator

from discord.ext import commands

import enums
from objects import Operation


class Lowered(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return argument.lower()
        except Exception:
            raise commands.BadArgument("WIP")


class TriggerConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return enums.Trigger[argument.upper()]
        except Exception:
            raise commands.BadArgument("WIP")


class OperationConverter(commands.Converter):
    OPERATORS = {
        "add": Operation(operator.add, "+"),
        "sub": Operation(operator.sub, "-"),
        "mul": Operation(operator.mul, "x"),
        "div": Operation(operator.floordiv, "÷")
    }

    async def convert(self, ctx, argument):
        argument = argument.lower()
        operator_found = self.OPERATORS.get(argument)

        if operator_found:
            return operator_found
        raise commands.BadArgument("WIP")
