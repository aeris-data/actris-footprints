class AbstractDictionary:
    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, key):
        raise NotImplementedError

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class AbstractCacheDictionary(AbstractDictionary):
    def __init__(self, *args, **kwargs):
        self._dict = {}
        self._keys = set()
        self._keys_not_found = set()
        super().__init__(*args, **kwargs)

    def __contains__(self, key):
        if key in self._dict or key in self._keys:
            return True
        elif key in self._keys_not_found:
            return False
        else:
            contains = super().__contains__(key)
            if contains:
                self._keys.add(key)
            else:
                self._keys_not_found.add(key)
            return contains

    def __getitem__(self, key):
        if key not in self._dict:
            value = super().__getitem__(key)
            self._dict[key] = value
            return value
        else:
            return self._dict[key]

    def get_cache(self):
        return list(self._dict.values())
