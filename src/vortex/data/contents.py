#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import collections

class DataContent(object):
    """Root class for data contents used by resources."""

    def __init__(self, **kw):
        self._data = None
        self._io = None
        self._size = 0
        self._filled = False
        for k, v in kw.iteritems():
            self.__dict__['_'+k] = v

    @classmethod
    def shellexport(cls):
        """Return current class name for shell export mechanism."""
        return str(cls.__name__)

    @property
    def updated(self):
        return False

    def slurp(self, container):
        """Abstract method."""
        pass

    def rewrite(self, container):
        """Abstract method."""
        pass


class AlmostDictContent(DataContent):
    """Implement some dictionary-like functions."""

    def __init__(self, **kw):
        if 'data' not in kw or not kw['data']:
            kw['data'] = dict()
        super(AlmostDictContent, self).__init__(**kw)

    def fmtkey(self, key):
        """Reshape entry keys of the internal dictionary."""
        return key

    def __getitem__(self, idx):
        return self._data[self.fmtkey(idx)]

    def __setitem__(self, idx, value):
        self._data[self.fmtkey(idx)] = value

    def __delitem__(self, idx):
        del self._data[self.fmtkey(idx)]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        for t in self._data.keys():
            yield t

    def __contains__(self, item):
        return self.has_key(self.fmtkey(item))

    def has_key(self, item):
        return self.fmtkey(item) in self._data

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def get(self, *args):
        return self._data.get(*args)

    def items(self):
        return self._data.items()

    def iteritems(self):
        return self._data.iteritems()


class IndexedTable(AlmostDictContent):
    """
    Multi-columns table indexed by first column.
    Behaves mostly as a dictionary.
    """

    def add(self, addlist):
        """Insert data according to index position given as the first item of ``addlist``."""
        for idxinput in addlist:
            i = idxinput.pop(0)
            self._data[self.fmtkey(i)] = idxinput

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.add([ x.split() for x in container.readlines() ])


class DataRaw(DataContent):
    """
    Multi-line raw data (no format assumed).
    Behaves mostly as a list.
    """

    def __init__(self, data=None, window=0, filled=False):
        if not data:
            if window:
                data = collections.deque(maxlen=window)
            else:
                data = list()
        super(DataRaw, self).__init__(data=data, window=window)

    def add(self, addlist):
        """Extend internal data contents with items of the ``addlist``."""
        self._data.extend(addlist)

    def clear(self):
        """Clear all internal data contents."""
        self._data[:] = []

    def __delitem__(self, idx):
        del(self._data[idx])

    def __delslice__(self, istart, iend):
        del(self._data[istart:iend])

    def __setitem__(self, idx, value):
        self._data[idx] = value

    def __setslice__(self, istart, iend, value):
        self._data[istart:iend] = value

    def __getitem__(self, idx):
        return self._data[idx]

    def __getslice__(self, istart, iend):
        return self._data[istart:iend]

    def __sizeof__(self):
        return self._data.__sizeof__()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        for t in self._data:
            yield t

    def __call__(self):
        return self._data

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        end = False
        while not end:
            data, end = container.dataread()
            self._data.append(data)
            if self._window and len(self._data) >= self._window:
                end = True

