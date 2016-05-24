#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines common base classes for miscellaneous purposes.
"""

#: No automatic export
__all__ = []

import collections
import datetime
import pprint
import json

import footprints
logger = footprints.loggers.getLogger(__name__)


class Foo(object):
    """Void C-struct like class... for gathering anything."""
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __getattr__(self, attr):
        return getattr(self.__dict__, attr)

    def __str__(self):
        return str(self.__dict__)


class Utf8PrettyPrinter(pprint.PrettyPrinter, object):
    """
    An utf-8 friendly version of the standard pprint.

    This class may be used like the original, e.g.:
       pf = Utf8PrettyPrinter().pformat
       print 'an_object:', pf(vars(an_object))
    """
    def __init__(self, *args, **kw):
        super(Utf8PrettyPrinter, self).__init__(*args, **kw)

    def format(self, obj, context, maxlevels, level):
        """Use readable representations for str and unicode, instead of repr."""
        if isinstance(obj, str):
            return obj, True, False
        if isinstance(obj, unicode):
            return obj.encode('utf8'), True, False
        return pprint.PrettyPrinter.format(self, obj, context, maxlevels, level)


class History(footprints.util.GetByTag):
    """Multi-purpose history like object."""

    def __init__(self, status=False, maxlen=None):
        self._history = collections.deque(maxlen=maxlen)
        self._status = status
        self._count = 0

    @property
    def count(self):
        return self._count

    @property
    def size(self):
        return self._history.maxlen

    def resize(self, maxlen=None):
        """Resize the internal history log to the specified length."""
        self._history = collections.deque(self._history, maxlen=maxlen)
        return self._history.maxlen

    def nice(self, item):
        """Try to build some nice string of the item."""
        if type(item) is list or type(item) is tuple:
            niceitem = ' '.join([str(x) for x in item])
        else:
            niceitem = item
        return niceitem

    def __iter__(self):
        for item in self._history:
            yield item

    def __len__(self):
        return len(self._history)

    def __getitem__(self, key):
        return self._history[key+1]

    def __setitem__(self, key, value):
        logger.warning('Could not set a value to a history item.')

    def __delitem__(self, key):
        logger.warning('Could not delete a value of a history item.')

    def grep(self, key):
        """Match the ``key`` in the string representation of history items."""
        return [ (count, stamp, item) for count, stamp, item in self._history if key in self.nice(item) ]

    def __contains__(self, key):
        return bool(self.grep(key))

    def stamp(self):
        """Return a time stamp."""
        return datetime.datetime.now()

    def append(self, *items):
        """Add the specified ``items`` as a new history entry."""
        stamp = self.stamp()
        if items:
            self._count += 1
            self._history.append((self._count, stamp, items))
        return (self._count, stamp)

    def get(self, start=1, end=None):
        """
        Extract history entries with a count value contained
        in the inclusive interval ``start`` - ``end``.
        """
        if end is None:
            end = self._count
        return [ (c, t, i) for c, t, i in self._history if start <= c <= end ]

    def show(self, start=1, end=None):
        """
        Display a numbered list of history items with a count value contained
        in the inclusive interval ``start`` - ``end``.
        """
        for c, t, i in self.get(start, end):
            print '[', str(c).rjust(4), '] :', self.nice(i)

    def showlast(self):
        """Display the last entry of the current history."""
        return self.show(start=self._count)

    def getaround(self, focus, delta=60):
        """
        Extract history entries with a stamp value contained
        in the exclusive interval [``focus`` - ``delta``, ``focus`` + ``delta``].
        """
        delta = datetime.timedelta(0, delta)
        return [ (c, t, i) for c, t, i in self._history if abs(t-focus) < delta ]

    def around(self, focus=None, delta=60):
        """
        Display a numbered list of history items with a stamp value contained
        in the exclusive interval [``focus`` - ``delta``, ``focus`` + ``delta``].
        """
        if focus is None:
            focus = self.stamp()
        for c, t, i in self.getaround(focus, delta):
            print '[', str(c).rjust(4), 'at', t, '] :', self.nice(i)

    def __call__(self):
        return self.show()

    @property
    def last(self):
        return self._history[-1][-1] if self.count else None

    def merge(self, *others):
        """Merge current history with other history objects."""
        pass


class Tracker(object):
    """Handling of simple state status through ``deleted``, ``created`` or ``updated`` items."""

    def __init__(self, before=None, after=None, deleted=None, created=None, updated=None, unchanged=None):
        if before is not None and after is not None:
            before = frozenset(before)
            after  = frozenset(after)
            self._deleted = before - after
            self._created = after - before
            self._unchanged = before & after
        else:
            self._unchanged = frozenset()
            self._set_deleted(deleted)
            self._set_created(created)
            self._set_unchanged(unchanged)
        self._updated = frozenset()
        self._set_updated(updated)

    def __str__(self):
        return '{0:s} | deleted={1:d} created={2:d} updated={3:d} unchanged={4:d}>'.format(
            repr(self).rstrip('>'),
            len(self.deleted), len(self.created), len(self.updated), len(self.unchanged)
        )

    def _get_deleted(self):
        return self._deleted

    def _set_deleted(self, value):
        if value is not None:
            try:
                self._deleted = frozenset(value)
                self._unchanged = self._unchanged - self._deleted
            except TypeError:
                self._deleted = frozenset()

    deleted = property(_get_deleted, _set_deleted, None, None)

    def _get_created(self):
        return self._created

    def _set_created(self, value):
        if value is not None:
            try:
                self._created = frozenset(value)
                self._unchanged = self._unchanged - self._created
            except TypeError:
                self._created = frozenset()

    created = property(_get_created, _set_created, None, None)

    def _get_updated(self):
        return self._updated

    def _set_updated(self, value):
        if value is not None:
            try:
                self._updated = frozenset(value)
                self._unchanged = self._unchanged - self._updated
            except TypeError:
                self._updated = frozenset()

    updated = property(_get_updated, _set_updated, None, None)

    def _get_unchanged(self):
        return self._unchanged

    def _set_unchanged(self, value):
        if value is not None:
            try:
                self._unchanged = frozenset(value)
                self._updated = self._updated - self._unchanged
            except TypeError:
                self._unchanged = frozenset()

    unchanged = property(_get_unchanged, _set_unchanged, None, None)

    def __contains__(self, item):
        return item in self.deleted or item in self.created or item in self.updated or item in self.unchanged

    def __iter__(self):
        for item in self.deleted | self.created | self.updated | self.unchanged:
            yield item

    def __len__(self):
        return len(self.deleted | self.created | self.updated)

    def dump(self, *args):
        """Produce a simple dump report."""
        if not args:
            args = ('deleted', 'created', 'updated', 'unchanged')
        for section in args:
            print 'Section {0:s}: {1:s}'.format(section, str(getattr(self, section)))

    def differences(self):
        """Dump only created, deleted and updated items."""
        return self.dump('deleted', 'created', 'updated')


class ShellEncoder(json.JSONEncoder):
    """Encoder for :mod:`json` dumps method."""

    def default(self, obj):
        """Overwrite the default encoding if the current object has a ``export_dict`` method."""
        if hasattr(obj, 'export_dict'):
            return obj.export_dict()
        elif hasattr(obj, 'footprint_export'):
            return obj.footprint_export()
        elif hasattr(obj, '__dict__'):
            return vars(obj)
        return super(ShellEncoder, self).default(obj)


class ReadOnlyDict(collections.Mapping):
    """A type of readonly dictionnary."""

    def __init__(self, data=dict()):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return repr(self._data)

    def __str__(self):
        return str(self._data)
