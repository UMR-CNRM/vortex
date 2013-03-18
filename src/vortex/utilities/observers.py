#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Various gateways to observing systems.

Using the factory :func:`classobserver` should provide a convenient way to register
to an undetermined number of objects hold by :class:`ObserverSet` objects.
"""

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger


_obstable = dict()

def classobserver(clsname):
    """Return an observer for the specifief class name."""
    if clsname not in _obstable:
        _obstable[clsname] = ObserverSet(tag=clsname)
    return _obstable[clsname]


class Observer(object):
    """
    Pseudo-Interface class. These three methods should be implemented
    by any Observer object.
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
    It holds two lists: the one of objects that are abserved and
    an other list of observers, listening to any creation, deletion
    or update of the observed objects.
    """

    def __init__(self, tag='void', incontext=False):
        self.tag = tag
        self._listen = set()
        self._items = set()

    def register(self, remote):
        """
        Push the ``remote`` object to the list of listening objects.
        A listening object should implement the :class:`Observer` interface.
        """
        self._listen.add(remote)

    def unregister(self, remote):
        """Remove the ``remote`` object from the list of listening objects."""
        self._listen.discard(remote)

    def notify_new(self, item, info):
        """Notify the listening objects that a new observed object is born."""
        self._items.add(item)
        for remote in self._listen:
            remote.newobsitem(item, info)

    def notify_del(self, item, info):
        """Notify the listening objects that an observed object does not exists anymore."""
        if item in self._items:
            self._items.discard(item)
            for remote in self._listen:
                remote.delobsitem(item, info)

    def notify_upd(self, item, info):
        """Notify the listening objects that an observed object has been updated."""
        if item in self._items:
            self._items.discard(item)
            for remote in self._listen:
                remote.updobsitem(item, info)
