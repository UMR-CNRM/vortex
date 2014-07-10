#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
This package defines some useful Design Patterns.
Implementations may be not the most efficient or
thread-safe proof ones, but still, for the time being,
it is enough to satisfy our small needs.
"""

from vortex.autolog import logdefault as logger

__all__ = [ 'Borg', 'Singleton' ]


class Borg(object):
    """A base class for sharing a common state by differents objects."""
    __state = {}

    def __new__(cls, *p, **k):
        logger.debug('Request a borg %s', cls)
        self = object.__new__(cls)
        self.__dict__ = cls.__state
        logger.debug('New borg %s', self)
        return self


class Singleton(object):
    """Obviously a base class for any *real* singleton."""

    def __new__(cls, *p, **k):
        logger.debug('Request a singleton %s', cls)
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
            logger.debug('Building a brand new singleton %s', cls._instance)
        logger.debug('New singleton %s', cls._instance)
        return cls._instance

