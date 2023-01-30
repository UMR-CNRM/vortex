"""
Footprint utilities to handle the ``priority`` footprint's attribute.
"""

import functools

__all__ = ['top', ]


@functools.total_ordering
class PriorityLevel:
    """Single level to be used inside footprints."""

    def __init__(self, tagname, pset):
        self._tag = tagname
        if isinstance(pset, PrioritySet):
            self._pset = pset
        else:
            raise TypeError('argument `pset` should be a PrioritySet, not {!s}'.format(type(pset)))

    def __call__(self):
        return self.rank

    @property
    def tag(self):
        return self._tag

    @property
    def inset(self):
        return self._pset

    @property
    def rank(self):
        """Actual order level in the current set of priorities."""
        return self.inset.levelindex(self.tag)

    def __eq__(self, other):
        if not isinstance(other, PriorityLevel):
            try:
                other = self.inset.level(str(other))
            except (ValueError, TypeError):
                return False
        return self.rank == other.rank

    def __gt__(self, other):
        if not isinstance(other, PriorityLevel):
            other = self.inset.level(str(other))
        return self.rank > other.rank

    def delete(self):
        """Removes itself from the priority set."""
        self.inset.remove(self.tag)

    def up(self):
        """Gain one step in the ranking."""
        return self.inset.rerank(self.tag, 1)

    def down(self):
        """Loose one step in the ranking."""
        return self.inset.rerank(self.tag, -1)

    def top(self):
        """Rerank as the top level priority."""
        return self.inset.rerank(self.tag, len(self.inset()))

    def bottom(self):
        """Rerank as the bottom level priority."""
        return self.inset.rerank(self.tag, -1 * len(self.inset()))

    def addafter(self, tag):
        """Add a new priority after the current one."""
        return self.inset.insert(tag, after=self.tag)

    def addbefore(self, tag):
        """Add a new priority before the current one."""
        return self.inset.insert(tag, before=self.tag)

    def nextlevel(self):
        """Return the next priority level in the set... if any."""
        return self.inset.levelbyindex(self.rank + 1)

    def prevlevel(self):
        """Return the previous priority level in the set... if any."""
        return self.inset.levelbyindex(self.rank - 1)

    def as_dump(self):
        """Return a nicely formated class name for dump in footprint."""
        return '{0.tag} (rank={0.rank:d})'.format(self)


class PrioritySet:
    """
    Iterable class for handling unsortable priority levels.
    """

    def __init__(self, levels=None):
        self._levels = list()
        if levels is not None:
            self.extend(*levels)
        self._freeze = dict(default=self._levels[:])

    def __iter__(self):
        yield from self._levels

    def __call__(self):
        return tuple(self._levels)

    def __len__(self):
        return len(self._levels)

    def __contains__(self, item):
        try:
            item = item.tag
        except AttributeError:
            pass
        return item.upper() in self.levels

    @property
    def levels(self):
        return tuple(self._levels)

    def level(self, tag):
        """Return the :class:`PriorityLevel` object of this set associated to the specified ``tag`` name."""
        if isinstance(tag, PriorityLevel):
            return tag
        pl = None
        if tag and str(tag).upper() in self._levels:
            pl = self.__dict__[str(tag).upper()]
        return pl

    def reset(self):
        """Restore the frozen defaults as defined at the initialisation phase."""
        self.restore('default')

    def freezed(self):
        """Return a tuple of tags used for naming past freezings."""
        return sorted(self._freeze.keys())

    def freeze(self, tag):
        """Store the current ordered list of priorities with a ``tag``."""
        tag = tag.lower()
        if tag == 'default':
            raise ValueError('Could not freeze a new default')
        else:
            self._freeze[tag] = self._levels[:]

    def restore(self, tag):
        """Restore previously frozen defaults under the specified ``tag``."""
        self._levels = self._freeze[tag.lower()][:]
        for levelname in [x for x in self._levels if x not in self.__dict__]:
            self.__dict__[levelname] = PriorityLevel(levelname, pset=self)

    def extend(self, *levels):
        """
        Extends the set of logical names for priorities.
        Existing levels are reranked at top priority as well as new one.
        """
        for levelname in [x.upper() for x in levels]:
            while levelname in self._levels:
                self._levels.remove(levelname)
            self._levels.append(levelname)
            self.__dict__[levelname] = PriorityLevel(levelname, pset=self)

    def levelbyindex(self, ipos):
        """Returns the relative position of the priority named ``tag``."""
        if ipos < 0 or ipos >= len(self._levels):
            return None
        else:
            return self.__dict__[self._levels[ipos]]

    def levelindex(self, tag):
        """Returns the relative position of the priority named ``tag``."""
        tag = tag.upper()
        if tag not in self._levels:
            raise ValueError('No such level priority: {!s}'.format(tag))
        return self._levels.index(tag)

    def rerank(self, tag, upd):
        """Reranks the priority named ``tag`` according to ``upd`` shift. Eg: +1, -2, etc."""
        tag = tag.upper()
        ipos = self._levels.index(tag) + upd
        if ipos < 0:
            ipos = 0
        self._levels.remove(tag)
        self._levels.insert(ipos, tag)
        return self.level(tag)

    def remove(self, tag):
        """Remove the :class:`PriorityLevel` item associated to the specified ``tag`` name."""
        if isinstance(tag, PriorityLevel):
            tag = tag.tag
        else:
            tag = str(tag).upper()
        self._levels.remove(tag)
        del self.__dict__[tag]

    def insert(self, tag=None, after=None, before=None):
        """Insert a new priority after or before an other one (which the tag name is given)."""
        if tag is None:
            return None
        else:
            tag = str(tag).upper()
        self.extend(tag)
        if after is not None:
            self._levels.remove(tag)
            if isinstance(after, PriorityLevel):
                after = after.tag
            self._levels.insert(self._levels.index(after.upper()) + 1, tag)
        elif before is not None:
            self._levels.remove(tag)
            if isinstance(before, PriorityLevel):
                before = before.tag
            self._levels.insert(self._levels.index(before.upper()), tag)
        return self.level(tag)


#: Predefined ordered object.
top = PrioritySet(levels=['none', 'default', 'toolbox', 'debug'])


def set_before(priorityref, *args):
    """Set ``args`` priority before specified ``priorityref``."""
    for newpriority in args:
        top.insert(tag=newpriority, before=priorityref)


def set_after(priorityref, *args):
    """Set ``args`` priority after specified ``priorityref``."""
    for newpriority in reversed(args):
        top.insert(tag=newpriority, after=priorityref)
