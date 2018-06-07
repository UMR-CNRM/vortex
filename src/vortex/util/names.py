#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Functions and tools to handle resources names or other kind of names.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class VortexNameBuilderError(ValueError):
    pass


class VortexNameBuilder(object):
    """Basenames factory for resources handled by some Vortex like provider."""
    def __init__(self, *args, **kw):
        logger.debug('Init VortexNameBuilder %s', self.__class__)
        self._default = dict(
            radical    = 'vortexdata',
            src        = None,
            fmt        = None,
            term       = None,
            period     = None,
            geo        = None,
            suffix     = None,
            nativefmt  = None,
            stage      = None,
            part       = None,
            compute    = None,
            number     = None,
            filtername = None,
        )
        self.setdefault(**kw)

    def setdefault(self, **kw):
        """Update or set new default values as the background description used in packing."""
        self._default.update(kw)

    @property
    def defaults(self):
        """List of currently declared defaults (defined or not)."""
        return self._default.keys()

    def as_dump(self):
        """Nicely formated view of the current class in dump context."""
        return str(self._default)

    def pack(self, d):
        """Build the resource vortex basename according to ``style`` value."""
        components = dict()
        components.update(self._default)
        components.update(d)

        packstyle = getattr(self, 'pack_' + components.get('style', 'std'), self.pack_std)
        return packstyle(components)

    def pack_void(self, value):
        """The most trivial conversion mechanism: the ``value`` as string."""
        return str(value)

    def pack_std_item_seta(self, value):
        """Packing of a MPI-task number in first direction."""
        return 'a{0:04d}'.format(int(value))

    def pack_std_item_setb(self, value):
        """Packing of a MPI-task number in second direction."""
        return 'b{0:04d}'.format(int(value))

    def pack_std_item_mpi(self, value):
        """Packing of a MPI-task number."""
        return 'n{0:04d}'.format(int(value))

    def pack_std_item_openmp(self, value):
        """Packing of an OpenMP id number."""
        return 'omp{0:02d}'.format(int(value))

    def pack_std_item_month(self, value):
        """Packing of a month-number value."""
        return 'm' + str(value)

    def pack_std_item_stretching(self, value):
        """Packing of the stretching factor in spectral geometry."""
        return 'c' + str(int(value * 10))

    def pack_std_item_truncation(self, value):
        """Packing of the geometry's truncation value."""
        return 'tl' + str(value)

    def pack_std_item_filtering(self, value):
        """Packing of the geometry's filtering value."""
        return 'f' + str(value)

    def pack_std_item_time(self, value):
        """Packing of a Time object."""
        return value.fmthm if hasattr(value, 'fmthm') else str(value)

    pack_std_item_begintime = pack_std_item_time
    pack_std_item_endtime = pack_std_item_time

    def pack_std_item_cutoff(self, value):
        """Abbreviate the cutoff name."""
        cutoff_map = dict(production='prod')
        return cutoff_map.get(value, value)

    def pack_std_items(self, items):
        """
        Go through all items and pack them according to the so-called standard way.
        Result is always a list of string values.
        """
        if not isinstance(items, list):
            items = [items]
        packed = list()
        for i in items:
            if isinstance(i, dict):
                for k, v in i.items():
                    packmtd = getattr(self, 'pack_std_item_' + k, self.pack_void)
                    packed.append(packmtd(v))
            else:
                packed.append(self.pack_void(i))
        return packed

    def pack_std(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called standard style.
        """
        name = d['radical']

        if d['src'] is not None:
            name = name + '.' + '-'.join(self.pack_std_items(d['src']))

        if d['filtername'] is not None:
            name = name + '.' + d['filtername']

        if d['geo'] is not None:
            name = name + '.' + '-'.join(self.pack_std_items(d['geo']))

        if d['compute'] is not None:
            name = name + '.' + '-'.join(self.pack_std_items(d['compute']))

        if d['term'] is not None:
            name = name + '+' + '-'.join(self.pack_std_items(d['term']))
        else:
            if d['period'] is not None:
                name = name + '.' + '-'.join(self.pack_std_items(d['period']))

        if d['number'] is not None:
            name = name + '.' + '-'.join(self.pack_std_items(d['number']))

        if d['fmt'] is not None:
            name = name + '.' + d['fmt']

        if d['suffix'] is not None:
            name = name + '.' + '.'.join(self.pack_std_items(d['suffix']))

        return name.lower()

    def pack_obs(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called observation style.
        """
        if (d.get('nativefmt', None) is None):
            raise VortexNameBuilderError
        name = '.'.join([
            d['nativefmt'] + '-' + d.get('layout', 'std'),
            'void' if d['stage'] is None else d['stage'],
            'all' if d['part'] is None else d['part'],
        ])
        if d['suffix'] is not None:
            name = name + '.' + d['suffix']

        return name.lower()

    def pack_obsmap(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called observation-map style.
        """
        name = '.'.join((
            d['radical'],
            '-'.join(self.pack_std_items(d['stage'])),
            'txt' if d['fmt'] is None else d['fmt'],
        ))
        return name.lower()
