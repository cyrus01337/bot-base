class DottedDict(dict):
    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = DottedDict(value)
        super().__setitem__(key, value)

    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)

    def __getattr__(self, attr):
        return self.__getitem__(attr)
