"""
Proxy objects to footprints catalogs.
"""

from bronx.fancies import loggers
from bronx.patterns import getbytag
from bronx.syntax.decorators import secure_getattr

from . import collectors

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# Module interface

def get(**kw):
    """Return actual proxy object matching description."""
    return FootprintProxy(**kw)


def keys():
    """Return the list of current proxies tags."""
    return FootprintProxy.tag_keys()


def values():
    """Return the list of proxies values."""
    return FootprintProxy.tag_values()


def items():
    """Return the items of the proxies table."""
    return FootprintProxy.tag_items()


# Base class

class FootprintProxy(getbytag.GetByTag):
    """Access to alive footprint items."""

    def __call__(self):
        self.cat()

    def __iter__(self):
        """Iterates over collectors."""
        yield from collectors.values()

    def cat(self):
        """Print a list of all existing collectors."""
        for k, v in sorted(collectors.items()):
            print(str(len(v)).rjust(4), (k + 's').ljust(16), v)

    def catlist(self):
        """Return a list of tuples (len, name, collector) for all alive collectors."""
        return [(len(v), k + 's', v) for k, v in sorted(collectors.items())]

    def objects(self):
        """Print the list of all existing objects tracked by the collectors."""
        for k, c in sorted(collectors.items()):
            objs = c.instances()
            print(str(len(objs)).rjust(4), (k + 's').ljust(16), objs)

    def objectsmap(self):
        """Return a dictionary of instances sorted by collectors entries."""
        return {k + 's': c.instances() for k, c in collectors.items()}

    def exists(self, tag):
        """Check if a given ``tag`` of objects is tracked or not."""
        return tag.rstrip('s') in collectors.keys()

    def __contains__(self, item):
        """Similar as ``self.exists(item)``."""
        return self.exists(item)

    def getitem(self, item, value=None):
        """Mimic the get access of a dictionary for defined collectors."""
        if item in self:
            return collectors.get(tag=item)
        else:
            return value

    @secure_getattr
    def __getattr__(self, attr):
        """Gateway to collector (plural noun) or load method (singular)."""
        if attr.startswith('_') or attr not in self:
            return None
        else:
            if attr.endswith('s'):
                return collectors.get(tag=attr)
            else:
                return collectors.get(tag=attr).load
