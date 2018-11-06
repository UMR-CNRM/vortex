#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import collections

from vortex import sessions
from vortex.data.flow import FlowResource
from vortex.data.resources import Resource
from vortex.syntax.stdattrs import FmtInt
from vortex.syntax.stddeco import namebuilding_delete, namebuilding_insert
from vortex.data.contents import DataContent, JsonDictContent, FormatAdapter
from vortex.util.roles import setrole

#: No automatic export
__all__ = []


@namebuilding_insert('src', lambda s: [s.binary, s.task.split('/').pop()])
@namebuilding_insert('compute', lambda s: s.part)
@namebuilding_delete('fmt')
class Listing(FlowResource):
    """Miscellaneous application output from a task processing."""
    _footprint = [
        dict(
            info = 'Listing',
            attr = dict(
                task = dict(
                    optional = True,
                    default  = 'anonymous'
                ),
                kind = dict(
                    values   = ['listing']
                ),
                part = dict(
                    optional = True,
                    default  = 'all',
                ),
                binary = dict(
                    optional = True,
                    default  = '[model]',
                ),
                clscontents = dict(
                    default = FormatAdapter,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'listing'

    def olive_basename(self):
        """Fake basename for getting olive listings"""
        if hasattr(self, '_listingpath'):
            return self._listingpath
        else:
            return "NOT_IMPLEMENTED"

    def archive_basename(self):
        return "listing." + self.part


class ParallelListing(Listing):
    """Multi output for parallel MPI and/or OpenMP processing."""
    _footprint = [
        dict(
            attr = dict(
                kind = dict(
                    values = ['listing', 'plisting', 'mlisting'],
                    remap  = dict(
                        listing  = 'plisting',
                        mlisting = 'plisting',
                    )
                ),
                mpi = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '03'),
                ),
                openmp = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '02'),
                ),
                seta = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '03'),
                ),
                setb = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '02'),
                ),
            )
        )
    ]

    def namebuilding_info(self):
        """From base information of ``listing`` add mpi and openmp values."""
        info = super(ParallelListing, self).namebuilding_info()
        if self.mpi and self.openmp:
            info['compute'] = [{'mpi': self.mpi}, {'openmp': self.openmp}]
        if self.seta and self.setb:
            info['compute'] = [{'seta': self.seta}, {'setb': self.setb}]
        return info


@namebuilding_insert('src', lambda s: [s.binary, s.task.split('/').pop()])
@namebuilding_insert('compute', lambda s: s.part)
@namebuilding_delete('fmt')
class StaticListing(Resource):
    """Miscelanous application output from a task processing, out-of-flow."""
    _footprint = [
        dict(
            info = 'Listing',
            attr = dict(
                task = dict(
                    optional = True,
                    default  = 'anonymous'
                ),
                kind = dict(
                    values   = ['staticlisting']
                ),
                part = dict(
                    optional = True,
                    default  = 'all',
                ),
                binary = dict(
                    optional = True,
                    default  = '[model]',
                ),
                clscontents = dict(
                    default = FormatAdapter,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'staticlisting'


@namebuilding_insert('compute', lambda s: None if s.mpi is None else [{'mpi': s.mpi}, ],
                     none_discard=True)
class DrHookListing(Listing):
    """Output produced by DrHook"""
    _footprint = [
        dict(
            attr = dict(
                kind = dict(
                    values = ['drhook', ],
                ),
                mpi = dict(
                    optional = True,
                    type     = FmtInt,
                    args     = dict(fmt = '03'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'drhookprof'


class Beacon(FlowResource):
    """Output indicating the end of a model run."""
    _footprint = [
        dict(
            info = 'Beacon',
            attr = dict(
                kind = dict(
                    values   = ['beacon']
                ),
                clscontents = dict(
                    default = JsonDictContent,
                ),
                nativefmt = dict(
                    default = 'json',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'beacon'


@namebuilding_insert('src', lambda s: s.task.split('/').pop())
@namebuilding_insert('compute', lambda s: s.scope)
class TaskInfo(FlowResource):
    """Task informations."""
    _footprint = [
        dict(
            info = 'Task informations',
            attr = dict(
                task = dict(
                    optional = True,
                    default  = 'anonymous'
                ),
                kind = dict(
                    values   = ['taskinfo']
                ),
                scope = dict(
                    optional = True,
                    default  = 'void',
                ),
                clscontents = dict(
                    default = JsonDictContent,
                ),
                nativefmt = dict(
                    default = 'json',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'taskinfo'


class SectionsSlice(collections.Sequence):
    """Hold a list of dictionaries representing Sections."""

    _INDEX_PREFIX = 'sslice'
    _INDEX_ATTR = 'sliceindex'

    def __init__(self, sequence):
        self._data = sequence

    def __getitem__(self, i):
        if isinstance(i, six.string_types) and i.startswith(self._INDEX_PREFIX):
            i = int(i[len(self._INDEX_PREFIX):])
        return self._data[i]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def to_list(self):
        """Returns a list object with the exact same content."""
        return list(self._data)

    @staticmethod
    def _sloppy_lookup(item, k):
        """Look for a key *k* in the *item* dictionary and returns it.

        :note: A special treatment is made for the 'role' key (the role factory is used
        and the 'alternate' attribute may also be looked for).

        :note: if *k* is not found at the top level of the dictionary, the
        'resource', 'provider' and 'container' parts of the 'rh'sub-dictionary
        are also looked for.
        """
        if k == 'role':
            return item[k] or item['alternate']
        elif k in item:
            return item[k]
        elif k in item['rh']['resource']:
            return item['rh']['resource'][k]
        elif k in item['rh']['provider']:
            return item['rh']['provider'][k]
        elif k in item['rh']['container']:
            return item['rh']['container'][k]
        else:
            raise KeyError("'%s' wasn't found in the designated dictionary")

    def _sloppy_ckeck(self, item, k, v):
        """Perform a _sloppy_lookup and check the result against *v*."""
        if k in ('role', 'alternate'):
            v = setrole(v)
        try:
            found = self._sloppy_lookup(item, k)
            return found == v
        except KeyError:
            return False

    def filter(self, **kwargs):
        """Create a new :class:`SectionsSlice` object that will be filtered using *kwargs*.

        :example: To retrieve sections with ``role=='Guess'`` and ``rh.provider.member==1``::

            >>> self.filter(role='Guess', member=1)
        """
        newslice = [s for s in self
                    if all([self._sloppy_ckeck(s, k, v) for k, v in kwargs.items()])]
        return self.__class__(newslice)

    def uniquefilter(self, **kwargs):
        """Like :meth:`filter` but checks that only one element matches."""
        newslice = self.filter(** kwargs)
        if len(newslice) == 0:
            raise ValueError("No section was found")
        elif len(newslice) > 1:
            raise ValueError("Multiple sections were found")
        else:
            return newslice

    @property
    def indexes(self):
        """Returns an index list of all the element contained if the present object."""
        return [self._INDEX_PREFIX + '{:d}'.format(i) for i in range(len(self))]

    def __getattr__(self, attr):
        """Provides an easy access to content's data with footprint's mechanisms.*

        If the present :class:`SectionsSlice` only contains one element, a
        :meth:`_sloppy_lookup` is performed on this unique element and returned.
        For exemple ``self.vapp`` will be equivalent to
        ``self[0]['rh']['provider']['vapp']``.

        If the present :class:`SectionsSlice` contains several elements, it's more
        complex : a callback function is returned. Such a callback can be used
        in conjunction with footprint's replacement mechanism. Provided that a
        ``{idx_attr:s}`` attribute exists in the footprint description and
        can be used as an index in the present object (such a list of indexes can
        be generated using the :meth:`indexes` property), the corresponding element
        will be searched using :meth:`_sloppy_lookup`.
        """.format(idx_attr=self._INDEX_ATTR)
        if len(self) == 1:
            try:
                return self._sloppy_lookup(self[0], attr)
            except KeyError:
                raise AttributeError("%s wasn't found in the unique dictionary", attr)
        elif len(self) == 0:
            raise AttributeError("The current SectionsSlice is empty. No attribute lookup allowed !")
        else:
            def _attr_lookup(g, x):
                if len(self) > 1 and (self._INDEX_ATTR in g or self._INDEX_ATTR in x):
                    idx = g.get(self._INDEX_ATTR, x.get(self._INDEX_ATTR))
                    try:
                        return self._sloppy_lookup(self[idx], attr)
                    except KeyError:
                        raise AttributeError("'%s' wasn't found in the %d-th dictionary", attr, idx)
                else:
                    raise AttributeError("A '%s' attribute must be there !", self._INDEX_ATTR)
            return _attr_lookup


class SectionsJsonListContent(DataContent):
    """Load/Dump a JSON file that contains a list of Sections.

    The conents of the JSON file is then stored in a query-able
    :class:`SectionsSlice` object.
    """

    def slurp(self, container):
        """Get data from the ``container``."""
        t = sessions.current()
        container.rewind()
        self._data = SectionsSlice(t.sh.json_load(container.iotarget()))
        self._size = len(self._data)

    def rewrite(self, container):
        """Write the data in the specified container."""
        t = sessions.current()
        container.close()
        mode = container.set_wmode(container.mode)
        iod = container.iodesc(mode)
        t.sh.json_dump(self.data.to_list(), iod, indent=4)
        container.updfill(True)


@namebuilding_insert('src', lambda s: s.task.split('/').pop())
class SectionsList(FlowResource):
    """Class to handle a resource that contains a list of Sections in JSON format.

    Such a resource can be generated using the :class:`FunctionStore` with the
    :func:`vortex.util.storefunctions.dumpinputs` function.
    """

    _footprint = dict(
        info = 'A Sections List',
        attr = dict(
            kind=dict(
                values=['sectionslist', ],
            ),
            task = dict(
                optional = True,
                default  = 'anonymous'
            ),
            clscontents = dict(
                default = SectionsJsonListContent,
            ),
            nativefmt   = dict(
                values  = ['json', ],
                default = 'json',
            )
        )
    )

    @property
    def realkind(self):
        return "sectionslist"
