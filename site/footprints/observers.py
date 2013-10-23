#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Observing systems to be used in footprints package.

Using the factory :func:`getbyname` should provide a convenient way to register
to an undetermined number of items hold by :class:`ObserverSet` objects.
"""

#: No automatic export
__all__ = []

import logging
logger = logging.getLogger('footprints.observers')

import util

def getbyname(tag=None, _obstable=dict()):
    """Return an observer for the specified tag name (a class name for example)."""
    if tag is None:
        return _obstable.keys()
    if tag not in _obstable:
        _obstable[tag] = ObserverSet(tag=tag)
    return _obstable[tag]


class Observer(object):
    """
    Pseudo-Interface class.
    These three methods should be implemented by any Observer object.
    """

    def newobsitem(self, item, info):
        """A new ``item`` has been created. Some information is provided through the dict ``info``."""
        logger.info('Notified %s new item %s info %s', self, item, info)

    def delobsitem(self, item, info):
        """The ``item`` has been deleted. Some information is provided through the dict ``info``."""
        logger.info('Notified %s del item %s info %s', self, item, info)

    def updobsitem(self, item, info):
        """The ``item`` has been updated. Some information is provided through the dict ``info``."""
        logger.info('Notified %s upd item %s info %s', self, item, info)


class ObserverSet(object):
    """
    A ObserverSet provides an indirection for observing pattern.
    It holds two lists: the one of objects that are observed and
    an other list of observers, listening to any creation, deletion
    or update of the observed objects.
    """

    def __init__(self, tag='void', info=dict()):
        self.tag = tag
        self.info = info
        self._listen = util.Catalog(weak=True)
        self._items = util.Catalog(weak=True)

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

    def notify_new(self, item, info):
        """Notify the listening objects that a new observed object is born."""
        logger.info('Notify new %s info %s', repr(item), info)
        self._items.add(item)
        for remote in list(self._listen):
            remote.newobsitem(item, info)

    def notify_del(self, item, info):
        """Notify the listening objects that an observed object does not exists anymore."""
        if item in self._items:
            logger.info('Notify del %s info %s', repr(item), info)
            for remote in list(self._listen):
                remote.delobsitem(item, info)
            self._items.discard(item)

    def notify_upd(self, item, info):
        """Notify the listening objects that an observed object has been updated."""
        if item in self._items:
            logger.info('Notify upd %s info %s', repr(item), info)
            for remote in list(self._listen):
                remote.updobsitem(item, info)

