#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules handles a set of base classes which play a fundamental role
in the pickup mechanism. It defines a very generic kind of :class:`Catalog`
and a dedicated class devoted to collecting all the current loaded classes
which inherit from a given root class.
"""

#: No automatic export
__all__ = []

import sys, re
import observers
from vortex.autolog import logdefault as logger
from trackers import tracker


def get_table(_catalogtable=dict()):
    return _catalogtable

def get_track(_catalogtrack=dict()):
    return _catalogtrack

class Catalog(object):
    """
    Abstract class for managing a collection of *items*.
    The interface is very light : :meth:`clear` and :meth:`refill` !
    Of course a catalog is an iterable object. It is also callable,
    and then returns a copy of the list of its items.
    """

    def __init__(self, **kw):
        logger.debug('Abstract %s init', self.__class__)
        self._items = set()
        self._filled = False
        self.autofeed = True
        self.__dict__.update(kw)
        if self.autofeed:
            self.refill()

    @classmethod
    def fullname(self):
        """Returns a nicely formated name of the current class (dump usage)."""
        return '{0:s}.{1:s}'.format(self.__module__, self.__name__)

    def items(self):
        return list(self._items)

    def __iter__(self):
        """Catalog is iterable... at least!"""
        for c in self._items:
            yield c

    def __call__(self):
        return self.items()

    def __len__(self):
        return len(self._items)

    def add(self, *items):
        """Add the ``item`` entry in the current catalog."""
        for item in items:
            self._items.add(item)

    def discard(self, bye):
        """Remove the ``bye`` entry from current catalog."""
        self._items.discard(bye)

    def clear(self):
        """Completly clear the list of items previously recorded in this catalog."""
        self._items = set()

    def refill(self):
        """Abstract method to be implemented to feed the catalog."""
        pass

    def refresh(self, **kw):
        """Redo the init sequence."""
        kw.setdefault('tag', self.tag)
        if len(kw) > 1:
            self.__dict__.update(kw)
            self.refill()


class ClassesCollector(Catalog):
    """
    A class collector is devoted to the gathering of class references that inherit
    from a given class, according to some other optional criteria such as the path
    of the module which defines the class.
    """

    def __init__(self, **kw):
        logger.debug('Collector catalog init %s', self)
        self.included = False
        self.register = True
        self.track = True
        self.instances = Catalog()
        super(ClassesCollector, self).__init__(**kw)

    def refill(self):
        """Implements a feed method based on the exploration of :mod:`sys.modules`."""
        logger.debug('Refill catalog %s', self)
        self.clear()
        sm = sys.modules
        itemstack = list()
        for mname in filter(lambda x: self.remod.match(x) and sm[x], sm.keys()):
            logger.debug(' > Exploring module %s : %s', mname, sm[mname])
            dm = sm[mname].__dict__
            for item in dm:
                if filter(lambda x:
                    type(dm[item]) == x.__class__ and
                    issubclass(dm[item], x) and
                    (self.included or dm[item] != x) and
                    not dm[item].__dict__.get('_abstract', False),
                    self.classes
                ):
                    logger.debug(' > > Add item %s', item)
                    itemstack.append(dm[item])
        self._items = set(itemstack)
        if self.register:
            self.instances.clear()
            for cls in self._items:
                observers.classobserver(cls.fullname()).register(self)
        self._filled = True
        return len(self._items)

    def newobsitem(self, item, info):
        logger.debug('Notified %s new item %s', self, item)
        self.instances.add(item)

    def delobsitem(self, item, info):
        logger.debug('Notified %s del item %s', self, item)
        self.instances.discard(item)

    def updobsitem(self, item, info):
        logger.debug('Notified %s upd item %s', self, item)

    def pickup_attributes(self, desc):
        """Try to pickup inside the catalogue a item that could match the description."""
        logger.debug('Pick up a "%s" in description %s with catalog %s', self.itementry, desc, self)
        if self.itementry in desc:
            logger.debug('A %s is already defined %s', self.itementry, desc[self.itementry])
        else:
            desc[self.itementry] = self.findbest(desc)
        if desc[self.itementry]:
            desc = desc[self.itementry].cleanup(desc)
        else:
            logger.warning('No %s found in description %s', self.itementry, desc)
        return desc

    def findany(self, desc):
        """
        Returns the first item of the catalog that :meth:`couldbe`
        as described by argument ``desc``.
        """
        logger.debug('Search any %s in catalog %s', desc, self._items)
        for item in self._items:
            resolved, u_input = item.couldbe(desc)
            if resolved: return item(resolved, checked=True)
        return None

    def findall(self, desc):
        """
        Returns all the items of the catalog that :meth:`couldbe`
        as described by argument ``desc``.
        """
        logger.debug('Search all %s in catalog %s', desc, self._items)
        found = list()
        trcat = None
        if self.track and type(self.track) == bool:
            self.track = tracker(tag='fpresolve')
        if self.track:
            trcat = self.track.new_entry('catalog', self.fullname())
        for item in self._items:
            if trcat:
                trnode = self.track.add('class', item.fullname(), base=trcat)
                self.track.current(trnode)
            resolved, theinput = item.couldbe(desc, trackroot=self.track)
            if resolved: found.append((item, resolved, theinput))
        return found

    def findbest(self, desc):
        """
        Returns the best of the items returned byt the :meth:`findall` method
        according to potential priorities rules.
        """
        logger.debug('Search all %s in catalog %s', desc, self._items)
        candidates = self.findall(desc)
        if not candidates:
            return None
        if len(candidates) > 1:
            logger.warning('Multiple candidates for %s', desc)
            candidates.sort(key=lambda x: x[0].weightsort(x[2]), reverse=True)
            for i, c in enumerate(candidates):
                thisclass, u_resolved, theinput = c
                logger.warning(' > no.%d in.%d is %s', i+1, len(theinput), thisclass)
        topcl, topr, u_topinput = candidates[0]
        return topcl(topr, checked=True)


def cataloginterface(xmodule, xclass):
    """
    Implements in the specified module ``xmodule`` references to tuned functions:
    * catalog
    * pickup
    * load
    according to the proper base ``xclass`` class given as second argument.
    """

    def catalog(**kw):
        """
        Returns the current catalog from base class XCLASS.
        By default, type XCANDIDATES could be collected.
        """
        kw.setdefault('tag', 'default')
        logger.debug('Catalog method %s tag %s', xclass, kw['tag'])
        table = get_table().setdefault(xclass.tablekey(), dict())
        if not table.has_key(kw['tag']):
            table[kw['tag']] = xclass(**kw)
        else:
            table[kw['tag']].refresh(**kw)
        return table[kw['tag']]

    def pickup(rd):
        """
        Find any class in the current XCLASS catalog that could match the specified
        description ``rd`` given as a dictionary reference.
        Then, the matching class is instantiated with resolved attributes.
        Returns a list of dictionaries with possibily picked up objects.
        """
        return xmodule.catalog().pickup_attributes(rd)

    tmpclass = xclass(register=False, autofeed=False)
    itementry = tmpclass.itementry
    candidates = ', '.join([ ':class:`{0:s}.{1:s}`'.format(x.__module__, x.__name__) for x in tmpclass.classes ])

    def load(**kw):
        """
        Same as pickup but operates on an expanded dictionary.
        Return either ``None`` or an object compatible with XCLASS.
        """
        return pickup(kw).get(itementry, None)

    for floc in ( catalog, pickup, load ):
        floc.__doc__ = re.sub('XCLASS', ':class:`{0:s}.{1:s}`'.format(xmodule.__name__, xclass.__name__), floc.__doc__)
        floc.__doc__ = re.sub('XCANDIDATES', candidates, floc.__doc__)

    xmodule.catalog = catalog
    xmodule.pickup = pickup
    xmodule.load = load
    catalogtrack = get_track()
    catalogtrack[xclass.tablekey()] = xmodule.catalog

def autocatlist():
    catalogtrack = get_track()
    return catalogtrack.keys()

def autocatload(kind='systems', tag='default'):
    catalogtrack = get_track()
    return catalogtrack[kind](tag=tag)

def fromtable(kind='systems', tag='default'):
    return get_table()[kind].get(tag, None)



