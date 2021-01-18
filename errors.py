from typing import Iterable


class BotBaseError(Exception):
    pass


class TokenFileNotFound(BotBaseError):
    pass


class IntentsRequired(BotBaseError):
    def __init__(self, *intents: Iterable[str]):
        message = (", ").join(intents)
        super().__init__(message)

        self.intents = intents
