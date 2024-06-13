import os
import pathlib
import getpass


_tempdir = None


def get_tempdir():
    global _tempdir
    if _tempdir is None:
        p = pathlib.Path('/workdir') / getpass.getuser()
        if not os.access(p, os.W_OK):
            p = pathlib.Path.home()
        _tempdir = p / 'tmp'
        _tempdir.mkdir(exist_ok=True)
    return _tempdir
