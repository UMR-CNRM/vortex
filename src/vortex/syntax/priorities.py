#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = [ 'top' ]

from vortex.utilities.patterns import Singleton


class PriorityLevel(object):
    """
    Single level to be used inside footprints.
    """
    
    def __init__(self, tagname):
        self.tag = tagname

    def __call__(self):
        return self.value

    @property
    def inset(self):
        return PrioritySet()

    @property
    def value(self):
        """Actual order level in the current set of priorities."""
        return self.inset.levelvalue(self.tag)

    def up(self):
        """Gain one step in the ranking."""
        return self.inset.rank(self.tag, 1)

    def down(self):
        """Loose one step in the ranking."""
        return self.inset.rank(self.tag, -1)

    def top(self):
        """Rerank as the top level priority."""
        return self.inset.rank(self.tag, len(self.inset()))

    def bottom(self):
        """Rerank as the bottom level priority."""
        return self.inset.rank(self.tag, -1 * len(self.inset()))

    def dumpinfp(self):
        """Return a nicely formated class name for dump in footprint."""
        return "{0:s}.{1:s}('{2:s}')".format(self.__module__, self.__class__.__name__, self.tag)


class PrioritySet(Singleton):
    """
    Iterable class for handling unsortable priority levels.
    """

    def __init__(self, levels=[]):
        if levels: 
            self._levels = []
            self.extend(*levels)
            self._freeze = dict( default = self._levels[:] )

    def __iter__(self):
        for l in self._levels:
            yield l

    def __call__(self):
        return self._levels

    def reset(self):
        """Restore the frozen defaults as defined at the initialisation phase."""
        self._levels = self._freeze['default'][:]

    def freeze(self, tag):
        """Store the current ordered list of priorities with a ``tag``."""
        tag = tag.lower()
        if tag == 'default':
            raise Exception('Could not freeze a new default')
        else:
            self._freeze[tag] = self._levels[:]

    def restore(self, tag):
        """Restore previously frozen defaults under the specified ``tag``."""
        self._levels = self._freeze[tag.lower()][:]

    def extend(self, *levels):
        """
        Extends the set of logical names for priorities.
        Existing levels are reranked at top priority as well as new one.
        """
        for levelname in [ x.upper() for x in levels ]:
            while levelname in self._levels:
                self._levels.remove(levelname)
            self._levels.append(levelname)
            self.__dict__[levelname] = PriorityLevel(levelname)
            
    def levelvalue(self, tag):
        """Returns the relative position of the priority named ``tag``."""
        tag = tag.upper()
        if tag not in self._levels:
            raise Exception('No such level priority %s', tag)
        return self._levels.index(tag)

    def rank(self, tag, upd):
        """Reranks the priority named ``tag`` according to ``upd`` shift. Eg: +1, -2, etc."""
        tag = tag.upper()
        ipos = self._levels.index(tag) + upd
        if ipos < 0: ipos = 0
        self._levels.remove(tag)
        self._levels.insert(ipos, tag)


#: Predefined ordered object.
top = PrioritySet(levels = ['none', 'default', 'toolbox', 'olive', 'oper', 'debug'])

