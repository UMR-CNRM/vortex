#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import collections

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.util.structs import ReadOnlyDict


class DataContent(object):
    """Root class for data contents used by resources."""

    def __init__(self, **kw):
        self._datafmt   = None
        self._data      = None
        self._metadata  = ReadOnlyDict()
        self._size      = 0
        for k, v in kw.iteritems():
            self.__dict__['_' + k] = v

    def __getattr__(self, attr):
        """Forward get attribute request to internal data object."""
        return getattr(self.data, attr)

    def __enter__(self):
        """Enter a :keyword:`with` context."""
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit from :keyword:`with` context."""
        pass

    @property
    def data(self):
        """The internal data encapsulated."""
        return self._data

    @property
    def size(self):
        """The actual size of the contents."""
        return self._size

    @property
    def metadata(self):
        """Return the metadata of the ressource in the container (maybe empty)."""
        return self._metadata

    def metadata_check(self, resource, delta=None):
        """Check that the metadata of the resource in the container matches
        the attributes of the resource given as an argument.

        Prior to the comparison, the delta argument will be added to the
        attribute read in the container. For example, if delta=dict(date='-PT1H'),
        we will in fact check that the date of the resource in the container is
        one hour before the date specified in the resource's footprint.
        """
        if not len(self.metadata):
            logger.error('Metadata check is not implemented for this format. ' +
                         'The check will always succeed...')
        delta = delta or {}
        outcome = True
        for mkey, mval in self.metadata.iteritems():
            if hasattr(resource, mkey):
                cval = getattr(resource, mkey)
                if mkey in delta:
                    cval += delta[mkey]
                outcome = outcome and cval == mval
        if not outcome:
            logger.warning("The ressource in the container doesn't match the resource footprint: %s",
                           str(self.metadata))
        return outcome

    @property
    def datafmt(self):
        """The initial format of the contents."""
        return self._datafmt

    @classmethod
    def export_dict(cls):
        """Return current class name for shell or pure dict export mechanism."""
        return (cls.__module__, cls.__name__)

    @property
    def updated(self):
        return False

    def slurp(self, container):
        """Should be overwritten. Basically get the totalsize of the actual container."""
        self._size = container.totalsize

    def _merge_checkclass(self, *kargs):
        """Utility method to check that all the kargs objects are compatible self."""
        if not all([isinstance(obj, self.__class__) for obj in kargs]):
            raise ValueError("The object's types are not compatible with self")

    def merge(self, *kargs):
        """Merge several DataContents into one.

        This method have to be implemented and _merge_checkclass should be called
        to ensure that the object's types are compatible with self.
        """
        raise NotImplementedError("Merge is not implemented for this content.")

    def rewrite(self, container):
        """Abstract method."""
        pass


class UnknownContent(DataContent):
    """Fake DataContent subclass."""
    pass


class AlmostDictContent(DataContent):
    """Implement some dictionary-like functions."""

    def __init__(self, **kw):
        super(AlmostDictContent, self).__init__(**kw)
        if self._data is None:
            self._data = dict()

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
        """Dict-like behavior looking for the formatted ``item`` in internal data."""
        return self.fmtkey(item) in self._data

    def merge(self, *kargs):
        """Merge several data contents into one."""
        self._merge_checkclass(*kargs)
        for obj in kargs:
            self._data.update(obj.data)
            self._size += obj.size


class IndexedTable(AlmostDictContent):
    """
    Multi-columns table indexed by first column.
    Behaves mostly as a dictionary.
    """

    def append(self, item):
        """Insert data according to index position given as the first element of the ``item`` list."""
        if len(item) > 0:
            i = item.pop(0)
            self._data[self.fmtkey(i)] = item

    def extend(self, addlist):
        """Insert data according to index position given as the first item of ``addlist``."""
        for idxinput in addlist:
            self.append(idxinput)

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.extend([ x.split() for x in container.readlines() if not x.startswith('#') ])
        self._size = container.totalsize


class JsonDictContent(AlmostDictContent):
    """
    The internal data is supposed to be read from a json file.
    """

    @classmethod
    def _unicode2str(cls, jsdecode):
        """Try to convert Unicode string into *regular* strings"""
        if isinstance(jsdecode, dict):
            return {cls._unicode2str(key): cls._unicode2str(value)
                    for key, value in jsdecode.iteritems()}
        elif isinstance(jsdecode, list):
            return [cls._unicode2str(value) for value in jsdecode]
        elif isinstance(jsdecode, unicode):
            try:
                return jsdecode.encode()
            except UnicodeEncodeError:
                return jsdecode
        else:
            return jsdecode

    def slurp(self, container):
        """Get data from the ``container``."""
        t = sessions.current()
        container.rewind()
        self._data = t.sh.json_load(container.localpath())
        self._data = self._unicode2str(self._data)
        self._size = container.totalsize

    def rewrite(self, container):
        """Write the list contents in the specified container."""
        t = sessions.current()
        container.close()
        t.sh.json_dump(self.data, container.localpath(), indent=4)


class AlmostListContent(DataContent):
    """
    Implement some list-like functions.
    The argument maxprint is used for the maximum number of lines
    to display through the str function.
    """

    def __init__(self, **kw):
        self._maxprint = kw.pop('maxprint', 20)
        super(AlmostListContent, self).__init__(**kw)
        if self._data is None:
            self._data = list()

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

    def _get_maxprint(self):
        return self._maxprint

    def _set_maxprint(self, value):
        try:
            self._maxprint = abs(int(value))
        except (ValueError, TypeError):
            pass
        self._maxprint = max(10, self._maxprint)

    maxprint = property(_get_maxprint, _set_maxprint, None)

    def clear(self):
        """Clear all internal data contents."""
        self._data[:] = []

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.extend(container.readlines())
        self._size = container.totalsize

    def rewrite(self, container):
        """Write the list contents in the specified container."""
        container.close()
        for xline in self:
            container.write(xline)

    def merge(self, *kargs):
        """Merge several data contents into one."""
        self._merge_checkclass(*kargs)
        for obj in kargs:
            self._data.extend(obj.data)
            self._size += obj.size


class TextContent(AlmostListContent):
    """
    Multi-lines input text data split through blank seperator.
    Behaves mostly as a list.
    """

    def __init__(self, **kw):
        kw.setdefault('fmt', None)
        super(TextContent, self).__init__(**kw)

    def __str__(self):
        if len(self) > self.maxprint:
            catlist = self[0:3] + ['...'] + self[-3:]
        else:
            catlist = self[:]
        return '\n'.join([ str(x) for x in catlist ])

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.extend([ x.split() for x in container if not x.startswith('#') ])

    def formatted_data(self, item):
        """Return a formatted string according to optional internal fmt."""
        if self._fmt is None:
            return ' '.join([str(x) for x in item])
        else:
            return self._fmt.format(*item)

    def rewrite(self, container):
        """Write the text contents in the specified container."""
        container.close()
        for item in self:
            container.write(self.formatted_data(item) + '\n')


class DataRaw(AlmostListContent):
    """
    Multi-lines raw data (no format assumed).
    Behaves mostly as a list.
    """

    def __init__(self, data=None, window=0, fmt=None):
        if not data and window:
            data = collections.deque(maxlen=window)
        super(DataRaw, self).__init__(data=data, window=window, fmt=fmt)

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        end = False
        while not end:
            data, end = container.dataread()
            self._data.append(data)
            if self._window and len(self._data) >= self._window:
                end = True


class FormatAdapter(DataContent):
    """Adapter to objects that could manage a dedicated format."""
    def __init__(self, **kw):
        super(FormatAdapter, self).__init__(**kw)
        if self._data is None and footprints.proxy.dataformats is None:
            logger.warning('No collector for data formats')
            self._datafmt = None

    def __enter__(self):
        """
        Enter a :keyword:`with` context, setting some FORTRAN variables
        in order to switch off parallelism (in case of execution).
        """
        t = sessions.current()
        t.env.delta(
            LFI_HNDL_SPEC   = ':1',
            DR_HOOK_SILENT  = 1,
            DR_HOOK_NOT_MPI = 1,
            OMP_NUM_THREADS = 1,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit from :keyword:`with` context."""
        t = sessions.current()
        t.env.rewind()

    def slurp(self, container):
        """Load a dataformat object."""
        if self.datafmt:
            with self:
                self._data = footprints.proxy.dataformat(
                    filename       = container.abspath,
                    openmode       = 'r',
                    fmtdelayedopen = True,
                    format         = container.actualfmt.upper(),
                )
                # Look for a metadatareader object
                if self._data is not None and footprints.proxy.metadatareaders is not None:
                    mreader = footprints.proxy.metadatareader(
                        format     = container.actualfmt.upper(),
                    )
                    if mreader is not None:
                        mreader.content_init(self._data)
                        self._metadata = mreader


class MetaDataReader(footprints.FootprintBase):
    '''
    Abstract class for any MetaDataReader.

    Note: _do_delayed_init have to be subclassed. That's where the content of the
    container is actually read.
    '''

    _abstract  = True
    _collector = ('metadatareader',)
    _footprint = dict(
        info = 'Abstract MetaDataReader',
        attr = dict(
            format = dict(
                type     = str,
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        self._content_in = None
        self._datahide = None
        super(MetaDataReader, self).__init__(*kargs, **kwargs)

    @property
    def _data(self):
        '''Internal: check if one needs to intialise the _datahide dict.'''
        if self._datahide is None and self._content_in is not None:
            self._do_delayed_init()
        return self._datahide

    def content_init(self, thecontent):
        '''Set the data content that will be used to read the metadata'''
        self._content_in = thecontent

    def _do_delayed_init(self):
        '''Internal: actually initialise the _data array. Have to be subclassed !'''
        raise NotImplementedError

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def iteritems(self):
        for k in self:
            yield k, self[k]

    def __repr__(self):
        if self._datahide is None:
            return '{}: Not yet initialised'.format(self.__class__)
        else:
            return repr(self._data)

    def __str__(self):
        return str(self._data)
