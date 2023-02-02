"""
This package defines some useful Design Patterns.

Implementations may be not the most efficient or
thread-safe proof ones.
"""

from bronx.fancies import loggers

__all__ = []

logger = loggers.getLogger(__name__)


class Borg:
    """A base class for sharing a common state by different objects."""
    __state = {}

    def __new__(cls, *args, **kw):
        logger.debug('Request a borg %s', cls)
        self = object.__new__(cls)
        self.__dict__ = cls.__state
        logger.debug('New borg %s', self)
        return self


class Singleton:
    """Obviously a base class for any *real* singleton."""

    def __new__(cls, *args, **kw):
        logger.debug('Request a singleton %s', cls)
        if '_instance' not in cls.__dict__:
            cls._instance = object.__new__(cls)
            logger.debug('Building a brand new singleton %s', cls._instance)
        logger.debug('New singleton %s', cls._instance)
        return cls._instance
