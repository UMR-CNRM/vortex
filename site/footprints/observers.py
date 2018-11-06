#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Observing systems to be used in footprints package.

Using the factory :func:`get` should provide a convenient way to register
to an undetermined number of items hold by :class:`ObserverBoard` objects.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import copy

from . import loggers, util

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def get(**kw):
    """
    Return an :class:`ObserverBoard` objects for the specified tag name
    (a class name for example).
    """
    return ObserverBoard(**kw)


def keys():
    """Return actual tags names of the instantiated :class:`ObserverBoard` objects."""
    return ObserverBoard.tag_keys()


def values():
    """Return actual values of the instantiated :class:`ObserverBoard` objects."""
    return ObserverBoard.tag_values()


def items():
    """Return the items of the :class:`ObserverBoard` objects collection."""
    return ObserverBoard.tag_items()


class Observer(object):
    """
    Pseudo-Interface class.
    The three public methods should be implemented by any Observer object.
    """

    def _debuglogging(self, msg, *kargs):
        logger.debug('Notified %s ' + msg, self, *kargs)

    def newobsitem(self, item, info):
        """A new ``item`` has been created. Some information is provided through the dict ``info``."""
        self._debuglogging('new item %s info %s', item, info)

    def delobsitem(self, item, info):
        """The ``item`` has been deleted. Some information is provided through the dict ``info``."""
        self._debuglogging('del item %s info %s', item, info)

    def updobsitem(self, item, info):
        """The ``item`` has been updated. Some information is provided through the dict ``info``."""
        self._debuglogging('upd item %s info %s', item, info)


class ParrotObserver(Observer):
    """Like :class:`Observer` but boosts the verbosity (useful for tests)."""

    def _debuglogging(self, msg, *kargs):
        logger.info('Notified %s ' + msg, self, *kargs)


class SecludedObserverBoard(object):
    """A SecludedObserverBoard provides an indirection for the observing pattern.

    It holds two lists: one list of objects that are observed and
    another list of observers, listening to any creation, deletion
    or update of the observed objects.
    """

    def __init__(self):
        self._listen = util.Catalog(weak=True)
        self._items  = util.Catalog(weak=True)

    def __deepcopy__(self, memo):
        """No deepcopy expected, so ``self`` is returned."""
        return self

    def register(self, remote):
        """
        Push the ``remote`` object to the list of listening objects.
        A listening object should implement the :class:`Observer` interface.
        """
        self._listen.add(remote)

    def observers(self):
        """List of observing objects."""
        return list(self._listen)

    def observed(self):
        """List of observed objects."""
        return list(self._items)

    def unregister(self, remote):
        """Remove the ``remote`` object from the list of listening objects."""
        self._listen.discard(remote)

    def _extended_info(self, info):
        return info

    def notify_new(self, item, info):
        """Notify the listening objects that a new observed object is born."""
        logger.debug('Notify new %s info %s', repr(item), info)
        self._items.add(item)
        for remote in list(self._listen):
            remote.newobsitem(item, self._extended_info(info))

    def notify_del(self, item, info):
        """Notify the listening objects that an observed object does not exists anymore."""
        if item in self._items:
            logger.debug('Notify del %s info %s', repr(item), info)
            for remote in list(self._listen):
                remote.delobsitem(item, self._extended_info(info))
            self._items.discard(item)

    def notify_upd(self, item, info):
        """Notify the listening objects that an observed object has been updated."""
        if item in self._items:
            logger.debug('Notify upd %s info %s', repr(item), info)
            for remote in list(self._listen):
                remote.updobsitem(item, self._extended_info(info))


class ObserverBoard(SecludedObserverBoard, util.GetByTag):
    """
    Like a :class:`SecludedObserverBoard` but using the :class:`footprints.util.GetByTag`
    class to provide an easy access to existing boards.
    """

    def _extended_info(self, info):
        fullinfo = copy.copy(info)  # This is only a shallow copy...
        fullinfo['observerboard'] = self.tag
        return fullinfo
