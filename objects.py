from collections.abc import Callable


class Operation(object):
    def __init__(self, function: Callable, symbol: str):
        self._function = function
        self.symbol = symbol

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)
