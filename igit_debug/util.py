from typing import Iterator

from logbook import lookup_level


def safeiter(obj) -> Iterator:
    try:
        return iter(obj)
    except:
        return None


def parse_level(level):
    try:
        return lookup_level(level)
    except LookupError:
        return level