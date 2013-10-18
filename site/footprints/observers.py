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

import weakref


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
        self._listen = set()
        self._items = set()

    def __deepcopy__(self, memo):
        """No deepcopy expected, so ``self`` is returned."""
        return self

    def ref(self, o):
        """Provides the reference internaly stored, e.g., a weakref."""
        ro = None
        try:
            ro = weakref.ref(o)
        except AttributeError:
            logger.critical('No more weak referencing possible')
        finally:
            return ro

    def unref(self, r):
        """Return the actual referenced object if still alive."""
        return r()

    def register(self, remote):
        """
        Push the ``remote`` object to the list of listening objects.
        A listening object should implement the :class:`Observer` interface.
        """
        self._listen.add(self.ref(remote))

    def observers(self):
        """List of observing objects."""
        return [ x() for x in self._listen if x() is not None ]

    def observed(self):
        """List of observed objects."""
        return [ x() for x in self._items if x() is not None ]

    def unregister(self, remote):
        """Remove the ``remote`` object from the list of listening objects."""
        self._listen.discard(self.ref(remote))

    def notify_new(self, item, info):
        """Notify the listening objects that a new observed object is born."""
        self._items.add(self.ref(item))
        for remote in list(self._listen):
            rr = self.unref(remote)
            if rr is not None:
                rr.newobsitem(item, info)
            else:
                self._listen.discard(remote)

    def notify_del(self, item, info):
        """Notify the listening objects that an observed object does not exists anymore."""
        ri = self.ref(item)
        if ri is not None and ri in self._items:
            self._items.discard(ri)
            for remote in list(self._listen):
                rr = self.unref(remote)
                if rr is not None:
                    rr.delobsitem(item, info)
                else:
                    self._listen.discard(remote)

    def notify_upd(self, item, info):
        """Notify the listening objects that an observed object has been updated."""
        if self.ref(item) in self._items:
            for remote in list(self._listen):
                rr = self.unref(remote)
                if rr is not None:
                    rr.updobsitem(item, info)
                else:
                    self._listen.discard(remote)
