"""
This module is just a dummy overriding the warn function.
"""
from warnings import *
_warn = warn


def my_warning(message, category=RuntimeWarning, stacklevel=1, source=None):
    _warn(message.__repr__(), category, stacklevel, source)


warn = my_warning
