import re


class Tokenizer:
    _token = re.compile(r'\S+')
    #whitespaces = re.compile(r'\s+')

    def __init__(self, string):
        self._s = string
        self._pos = 0

    def __iter__(self):
        return self

    def __next__(self):
        match = Tokenizer._token.search(string=self._s, pos=self._pos)
        if match:
            self._pos = match.end()
            return match.group(0)
        else:
            raise StopIteration

    def skip(self, n):
        """
        Advances parser by a number of tokens

        :param n: number of tokens to skip
        :return: None or raises StopIteration if not enough tokens to parse
        """
        for i in range(n):
            next(self)

    def get(self, pos):
        """
        Retrieves a token and advance the parser past the token

        :param pos: zero-based index of the token
        :return: the token as string or raises StopIteration if the required token does not exists
        """
        self.skip(pos)
        return next(self)

    def remainder(self):
        """
        Gets the string not yet read by the parser but does not affect the parser's position

        :return: the string stripped with leading and trailing whitespaces if the string is not empty, otherwise None
        """
        rem = self._s[self._pos:].strip()
        return rem if rem else None

    def get_next_tokens(self, n, skip_tokens=0, convert=None):
        """
        Skips a number of tokens and gets the next ones and advance the parser past the last retrieved token

        :param n: number of tokens to retrieve
        :param skip_tokens: number of first tokens to skip
        :param convert: a function called for each retrieved token, e.g. float, int, etc.
        :return: a tuple of tokens as strings or raises StopIteration if not enough tokens to parse
        """
        self.skip(skip_tokens)
        if convert is None:
            return tuple(next(self) for i in range(n))
        else:
            return tuple(convert(next(self)) for i in range(n))


def tokenizer_generator(stream):
    while True:
        line = stream.readline()
        if line:
            yield Tokenizer(line)
        else:
            break
