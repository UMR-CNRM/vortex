"""
An empty module to be filled with some kind of blackholes objects.
"""

from bronx.fancies import loggers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class DataConst:
    """Constants stored as raw attributes."""

    def __init__(self, **kw):
        self.__dict__.update(kw)
        logger.debug("DataConst init %s", self)

    def __str__(self):
        return super().__str__() + " : " + str(sorted(self.__dict__.keys()))

    def __contains__(self, item):
        return item in self.__dict__
