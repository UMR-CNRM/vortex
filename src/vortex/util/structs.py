#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines common base classes for miscellaneous purposes.
"""

#: No automatic export
__all__ = []

import collections
import datetime
import functools
import pprint
import json
import pickle

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


class PrivateHistory(object):
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
        return self._history[key + 1]

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
        return [(c, t, i) for c, t, i in self._history if abs(t - focus) < delta]

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


class History(PrivateHistory, footprints.util.GetByTag):
    """Shared Multi-purpose history like object."""
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


class _DataStoreEntryKey(object):
    """The key of any element stored in a DataStore class."""

    def __init__(self, kind, **kwargs):
        """
        :param object kind: The `kind` of data (must be hashable)
        :param dict kwargs: Any key/value pairs that describe the data (values
            must be hashable)
        """
        self._kind = kind
        self._extras = kwargs
        try:
            self._hash = hash(tuple([kind, ] +
                                    [(k, v) for k, v in self._extras.iteritems()]))
        except TypeError:
            logger.critical('kind and extra arguments values must be hashable.')
            raise

    def __repr__(self):
        return '<{:s} object | {!s}>'.format(self.__class__.__name__, self)

    def __str__(self):
        extras_str = (' ' + ' '.join(['{!s}={!r}'.format(k, v) for k, v in self])).rstrip()
        return 'kind={!r}{:s}'.format(self.kind, extras_str)

    @property
    def kind(self):
        """The kind of the data."""
        return self._kind

    @property
    def extras(self):
        """Dictionary of key/value pairs that describe the data."""
        return self._extras.copy()  # This way, the user won't mess up things

    def __iter__(self):
        for k, v in self._extras.iteritems():
            yield (k, v)

    def __eq__(self, other):
        return self.kind == other.kind and self._extras == other.extras

    def __hash__(self):
        return self._hash

    def __getattr__(self, key):
        """Elements of extra are directly accessible."""
        if key.startswith('_'):
            raise AttributeError('Attribute not found')
        if key in self._extras:
            return self._extras[key]
        else:
            raise AttributeError('Attribute not found')


class DataStore(object):
    """An object that can store any pickable data. It acts like a small key/value database.

    * Keys are of :class:`_DataStoreEntryKey` class. They contain a
      mandatory `kind` attribute plus key/value pairs that describe the stored
      data more precisely.
    * Various methods are provided to access the entries.
    * Keys are indexed in order to perform fast searches (see the grep method).

    Data should always be pickalable so that the DataStore could be dumped to
    disk using the :meth:`pickle_dump` method.

    :example: Data should be inserted this way::

            ds = DataStore()
            ds.insert('kind_of_data', dict(key1='meaningful'),
                      'The data themselves...', readonly=True)
            ds.insert('kind_of_data', dict(key1='meaningful', key2='breathtaking'),
                      'More date...', readonly=True)
            ds.insert('kind_of_data', dict(), 'Another One', readonly=True)

        It could later be accessed::

            data = ds.get('kind_of_data', dict(key1='meaningful', key2='breathtaking'))
            print data
            More date...

        A search can be performed::

            dict_of_results = ds.grep('kind_of_data', dict(key1='meaningful'))
            print dict_of_results
            {<_DataStoreEntryKey object | kind='kind_of_data' key1='meaningful' key2='breathtaking'>: 'More date...',
             <_DataStoreEntryKey object | kind='kind_of_data' key1='meaningful'>: 'The data themselves...'}

        Finally the DataStore can be dumped/loaded to/from disk::

            ds.pickle_dump()
            another_ds = DataStore()
            another_ds.pickle_load()

    """

    _PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

    def __init__(self, default_picklefile='datastore.pickled'):
        """
        :param str default_picklefile: default name for the pickle dump file
        """
        self._pickle_dumpfile = default_picklefile
        self._reset_internal_state()

    def _reset_internal_state(self):
        self._store = dict()
        self._lock = dict()
        self._index = collections.defaultdict(functools.partial(collections.defaultdict,
                                                                set))

    def _index_update(self, key):
        self._index['kind'][key.kind].add(key)
        for k, v in key:
            self._index[k][v].add(key)

    def _index_remove(self, key):
        self._index['kind'][key.kind].remove(key)
        for k, v in key:
            self._index[k][v].remove(key)

    def _build_key(self, kind, extras):
        if not isinstance(extras, dict):
            raise ValueError("The 'extras' needs to be dictionary of hashables.")
        return _DataStoreEntryKey(kind, **extras)

    def insert(self, kind, extras, payload, readonly=True):
        """Insert a new ``payload`` data in the current DataStore.

        :param object kind: The kind of the ``payload`` data
        :param dict extras: Any key/value pairs that describe the ``payload`` data
        :param object payload: The data that will be stored
        :param bool readonly: Is the data readonly ?
        """
        key = self._build_key(kind, extras)
        if key in self._store and self._lock[key]:
            raise RuntimeError("This entry already exists and is read-only.")
        self._index_update(key)
        self._store[key] = payload
        self._lock[key] = readonly
        return payload

    def check(self, kind, extras):
        """Check if a data described by ``kind`` and ``extras`` exists in this DataStore.

        :param object kind: The kind of the expected data
        :param dict extras: Any key/value pairs that describe the expected data
        """
        key = self._build_key(kind, extras)
        return key in self._store

    def get(self, kind, extras, default_payload=None, readonly=True):
        """Retrieve data from the current DataStore.

        if the desired data is missing and ``default_payload`` is not `None`, a
        new entry is added to the DataStore using the ``default_payload`` and
        ``readonly`` arguments.

        :param object kind: The kind of the expected data
        :param dict extras: Any key/value pairs that describe the expected data
        :param object default_payload: Default data that may be stored and returned
        :param bool readonly: Is the default data readonly ?
        """
        key = self._build_key(kind, extras)
        try:
            return self._store[key]
        except KeyError:
            if default_payload is None:
                raise KeyError("No corresponding entry was found in the DataStore for {!r}".
                               format(key))
            else:
                self.insert(kind, extras, default_payload, readonly=readonly)
                return self._store[key]

    def delete(self, kind, extras, force=False):
        """Delete data from the current DataStore.

        :param object kind: The kind of the expected data
        :param dict extras: Any key/value pairs that describe the expected data
        """
        key = self._build_key(kind, extras)
        if not self._lock[key] or force:
            self._index_remove(key)
            del self._store[key]
            del self._lock[key]
        else:
            raise RuntimeError("This entry already exists and is read-only.")

    def grep(self, kind, extras):
        """Search for items that matches both ``kind`` and ``extras``.

        :note: When matching ``extras``, supernumerary attributes are ignored
            (e.g. ``extras=dict(a=1)`` will match ``dict(a=1, b=2)``)

        :param object kind: The kind of the expected data
        :param dict extras: Any key/value pairs that describe the expected data
        """
        if not isinstance(extras, dict):
            raise ValueError("The 'extras' needs to be dictionary of hashables.")
        result = self._index['kind'][kind].copy()
        for k, v in extras.iteritems():
            result &= self._index[k][v]
        return {k: self._store[k] for k in result}

    def grep_delete(self, kind, extras, force=False):
        """Search for items that matches both ``kind`` and ``extras`` and delete them.

        The dictionary of the removed key/data is returned.

        :note: When matching ``extras``, supernumerary attributes are ignored
            (e.g. ``extras=dict(a=1)`` will match ``dict(a=1, b=2)``)

        :param object kind: The kind of the expected data
        :param dict extras: Any key/value pairs that describe the expected data
        """
        grep = self.grep(kind, extras)
        for k in grep.keys():
            if not self._lock[k] or force:
                self._index_remove(k)
                del self._store[k]
                del self._lock[k]
            else:
                raise RuntimeError("This entry already exists and is read-only.")
        return grep

    def pickle_dump(self, dumpfile = None):
        """Pickle the content of the current DataStore and write it to disk.

        :param str dumpfile: Path to the dump file (if `None`, the default provided
            at the object creation time is used).
        """
        thefile = dumpfile or self._pickle_dumpfile
        with open(thefile, 'w') as pfh:
            pickle.dump((self._store, self._lock), pfh,
                        protocol=self._PICKLE_PROTOCOL)

    def pickle_load(self, dumpfile = None):
        """Read a pickle dump file from disk and refill the current DataStore.

        :param str dumpfile: Path to the dump file (if `None`, the default provided
            at the object creation time is used).
        """
        # Get the pickle file contents
        thefile = dumpfile or self._pickle_dumpfile
        with open(thefile, 'r') as pfh:
            unpickled = pickle.load(pfh)
        # Build the new store dictionary
        newstore = dict()
        for k, v in unpickled[0].iteritems():
            if k in self._store and hasattr(self._store[k], 'datastore_inplace_overwrite'):
                # In some particular cases, we want the an existing object to
                # reset itself. I guess we could call that an inplace overwrite
                self._store[k].datastore_inplace_overwrite(v)
                newstore[k] = self._store[k]
            else:
                newstore[k] = v
        # Update internals and rebuild the index
        self._reset_internal_state()
        self._store = newstore
        self._lock = unpickled[1]
        for k in self._store.iterkeys():
            self._index_update(k)

    def keys(self):
        """Return the list of available keys in this DataStore."""
        return self._store.keys()

    def __iter__(self):
        for k, v in self._store.iteritems():
            # Return copies of keys so that the _index WeakSet remain unperturbed
            yield (k, v)

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return '<{:s} object at {!s} | {:d} items>'.format(self.__class__.__name__,
                                                           hex(id(self)),
                                                           len(self))

    def __str__(self):
        outstr = ''
        for k, v in self:
            outstr += '{:10s} key  : {!s}\n'.format('read-only' if self._lock[k] else 'read-write', k)
            outstr += '{:10s} value: {!r}\n'.format('', v)
        return outstr


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


class FootprintCopier(footprints.FootprintBaseMeta):
    """A meta class that copies its content into to the target class.

    The _footprint class variable is dealt with properly (hopefully).
    """

    _footprint = None

    def __new__(cls, n, b, d):

        # Merge the footprints if necessary
        if cls._footprint is not None:
            if '_footprint' in d:
                fplist = list(cls._footprint)
                if isinstance(d['_footprint'], list):
                    fplist.extend(d['_footprint'])
                else:
                    fplist.append(d['_footprint'])
                d['_footprint'] = footprints.Footprint(*fplist, myclsname=n)
            else:
                d['_footprint'] = cls._footprint

        # Copy other things
        for var in [v for v in vars(cls) if
                    (not v.startswith('__') or v not in ('_footprint', )) and v not in d]:
            d[var] = getattr(cls, var)

        # Call super's new
        return super(FootprintCopier, cls).__new__(cls, n, b, d)
