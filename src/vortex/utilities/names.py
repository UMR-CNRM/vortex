#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Functions and tools to handle resources names or other kind of names.
"""

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger


class VNameBuilder(object):
    """Baseames factory for resources handled by some Vortex like provider."""
    def __init__(self, *args, **kw):
        logger.debug('New VNameBuilder %s', self.__class__)
        self._default = dict(
            radical = 'vortexdata',
            src = None,
            fmt = None,
            term = None,
            geo = None,
            suffix = None,
            nativefmt = None,
            stage = None,
            part = None,
            compute = None,
        )
        self.setdefault(**kw)

    def setdefault(self, **kw):
        """Update or set new default values as the background description used in packing."""
        self._default.update(kw)

    @property
    def defaults(self):
        """List of currently declared defaults (defined or not)."""
        return self._default.keys()

    def dumpshortcut(self):
        """Nicely formated view of the current class in dump context."""
        return "{0:s}.{1:s}({2:s})".format(self.__module__, self.__class__.__name__, str(self._default))

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
        return 'c' + str(int(value*10))

    def pack_std_item_truncation(self, value):
        """Packing of the geometry's truncation value."""
        return 'tl' + str(value)

    def pack_std_item_filtering(self, value):
        """Packing of the geometry's filtering value."""
        return 'f' + str(value)

    def pack_std_items(self, items):
        """
        Go through all items and pack them according to the so-called standard way.
        Result is always a list of string values.
        """
        if not type(items) == list:
            items = [ items ]
        packed = list()
        for i in items:
            if type(i) == dict:
                for k, v in i.iteritems():
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

        if d['src'] != None:
            name = name + '.' + '-'.join(self.pack_std_items(d['src']))

        if d['geo'] != None:
            name = name + '.' + '-'.join(self.pack_std_items(d['geo']))

        if d['compute'] != None:
            name = name + '.' + '-'.join(self.pack_std_items(d['compute']))

        if d['term'] != None:
            name = name + '+' + str(d['term'])

        if d['fmt'] != None:
            name = name + '.' + d['fmt']

        if d['suffix'] != None:
            name = name + '.' + '.'.join(self.pack_std_items(d['suffix']))

        return name.lower()

    def pack_obs(self,d):
        """
        Main entry point to convert a description into a file name
        according to the so-called observation style.
        """
        name = '.'.join([d['nativefmt'], d['stage'], d['part']])
        if d['suffix'] != None:
            name = name + '.' + d['suffix']

        return name.lower()

    def pack_obsmap(self,d):
        """
        Main entry point to convert a description into a file name
        according to the so-called observation-map style.
        """
        name = '.'.join([d['radical'], d['stage']])
        return name.lower()
