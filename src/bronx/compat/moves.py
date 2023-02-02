"""
Compatibility for modules or attributes that move or change their name across versions of Python
"""
import collections
import abc
import re
import sys


def _require_version(major, minor=0):
    """Check if the running python version is at least Python **major**.**minor**."""
    return (sys.version_info.major >= major and
            sys.version_info.minor >= minor)


# ABCs are moved from "collections" to "collections.abc" in 3.8
collections_abc = collections.abc
collections_abc.__doc__ = "retrocompatibility artifact when dealing with python 2 and 3 compatibility"


# re._pattern_type is removed in python3.7
class re_Pattern(metaclass=abc.ABCMeta):
    """Mimics Python3.7 re.Pattern behaviour."""

    def __new__(self, *args, **kwargs):
        """This is an abstract class."""
        raise TypeError("cannot create 're.Pattern' instances.")


if _require_version(3, 7):
    re_Pattern.register(re.Pattern)
else:
    re_Pattern.register(re.compile('^').__class__)
