#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Handling of footprints collectors.
Module's usage is mostly dedicated to main footprints package.
The footprints proxy could make some part of the interface visible as well.
"""

#: No automatic export
__all__ = []

import logging
logger = logging.getLogger('footprints.collectors')

from . import config, dump, reporting, util


# Module Interface

def get(**kw):
    """Return actual collector object matching description."""
    return Collector(**kw)

def keys():
    """Return the list of current entries names collected."""
    return Collector.tag_keys()

def values():
    """Return the list of current entries values collected."""
    return Collector.tag_values()

def items():
    """Return the items of the collectors table."""
    return Collector.tag_items()


# Base class

class Collector(util.GetByTag, util.Catalog):
    """
    A class collector is devoted to the gathering of class references that inherit
    from a given class (here a class with a footprint), according to some other optional criteria.
    """

    _tag_default = 'garbage'

    def __init__(self, **kw):
        logger.debug('Footprints collector init %s', self)
        self.instances = util.Catalog(weak=True)
        self.register = True
        self.report = True
        self.report_auto = True
        self.report_tag = None
        self.altreport = False
        for bc in self.__class__.__bases__:
            bc.__init__(self, **kw)
        if self.report_tag is None:
            self.report_tag = 'footprint-' + self.tag
        self.report_log = reporting.report(self.report_tag)
        config.add2proxies(self)

    @classmethod
    def tag_clean(cls, tag):
        return tag.rstrip('s')

    def newobsitem(self, item, info):
        """Register a new instance of some of the classes in the current collector."""
        logger.debug('Notified %s new item %s', self, item)
        self.instances.add(item)

    def delobsitem(self, item, info):
        """Unregister an existing object in the current collector of instances."""
        logger.debug('Notified %s del item %s', self, item)
        self.instances.discard(item)

    def updobsitem(self, item, info):
        """Not yet specialised..."""
        logger.debug('Notified %s upd item %s', self, item)

    def discard_kernel(self, rootname):
        """Discard from current collector classes with name starting with ``rootname``."""
        for x in [ cl for cl in self.items() if cl.fullname().startswith(rootname) ]:
            print 'Bye...', x
            self.discard(x)

    def pickup(self, desc):
        """Try to pickup inside the collector a item that could match the description."""
        logger.debug('Pick up a "%s" in description %s with collector %s', self.tag, desc, self)
        mkstdreport = desc.pop('_report', self.report_auto)
        mkaltreport = desc.pop('_altreport', self.altreport)
        for hidden in [ x for x in desc.keys() if x.startswith('_') ]:
            logger.warning('Hidden argument "%s" ignored in pickup attributes', hidden)
            del desc[hidden]
        if self.tag in desc and desc[self.tag] is not None:
            logger.debug('A %s is already defined %s', self.tag, desc[self.tag])
        else:
            desc[self.tag] = self.find_best(desc)
        if desc[self.tag] is not None:
            desc = desc[self.tag].cleanup(desc)
        else:
            dumper = dump.get()
            logger.warning('No %s found in description %s', self.tag, "\n" + dumper.cleandump(desc))
            if mkstdreport and self.report:
                print "\n", self.report_log.info(), "\n"
                self.report_last.lightdump()
                if mkaltreport:
                    altreport = self.report_last.as_flat()
                    altreport.reshuffle(['why', 'attribute'], skip=False)
                    altreport.fulldump()
                    altreport.reshuffle(['only', 'attribute'], skip=False)
                    altreport.fulldump()
        return desc

    def find_any(self, desc):
        """
        Return the first item of the collector that :meth:`couldbe`
        as described by argument ``desc``.
        """
        logger.debug('Search any %s in collector %s', desc, self._items)
        if self.report:
            self.report_log.add(collector=self)
        for item in self._items:
            resolved, u_input = item.couldbe(desc, report=self.report_log)
            if resolved:
                return item(resolved, checked=True)
        return None

    def find_all(self, desc):
        """
        Returns all the items of the collector that :meth:`couldbe`
        as described by argument ``desc``.
        """
        logger.debug('Search all %s in collector %s', desc, self._items)
        found = list()
        if self.report:
            self.report_log.add(collector=self)
        for item in self._items:
            resolved, theinput = item.couldbe(desc, report=self.report_log)
            if resolved:
                found.append((item, resolved, theinput))
        return found

    def find_best(self, desc):
        """
        Returns the best of the items returned byt the :meth:`find_all` method
        according to potential priorities rules.
        """
        logger.debug('Search all %s in collector %s', desc, self._items)
        candidates = self.find_all(desc)
        if not candidates:
            return None
        if len(candidates) > 1:
            dumper = dump.get()
            logger.warning('Multiple %s candidates for %s', self.tag, "\n" + dumper.cleandump(desc))
            candidates.sort(key=lambda x: x[0].weightsort(x[2]), reverse=True)
            for i, c in enumerate(candidates):
                thisclass, u_resolved, theinput = c
                logger.warning('  no.%d in.%d is %s', i+1, len(theinput), thisclass)
        topcl, topr, u_topinput = candidates[0]
        return topcl(topr, checked=True)

    def load(self, **desc):
        """Return the value matching current collector's tag after pickup of attributes."""
        return self.pickup(desc).get(self.tag, None)

    def default(self, **kw):
        """
        Try to find in existing instances tracked by the ``tag`` collector
        a suitable candidate according to description.
        """
        for inst in self.instances():
            if inst.reusable() and inst.compatible(kw):
                return inst
        return self.load(**kw)

    def grep(self, **kw):
        """
        Grep in the current instances of the collector items that match
        the set of attributes given as named arguments.
        """
        okmatch = list()
        for item in self.instances:
            ok = True
            for k, v in kw.items():
                if not hasattr(item, k) or getattr(item, k) != v:
                    ok = False
                    break
            if ok:
                okmatch.append(item)
        return okmatch

    def build_attrmap(self, attrmap=None, only=None):
        """Build a reversed attr-class map."""
        if attrmap is None:
            attrmap = dict()
        if only is not None and not hasattr(only, '__contains__'):
            only = (only,)
        for c in self:
            fp = c.retrieve_footprint()
            for k in [ ka for ka in fp.attr.keys() if ( only is None or ka in only ) ]:
                opt = ' (optional)' if fp.optional(k) else ''
                alist = attrmap.setdefault(k+opt, list())
                alist.append(dict(
                    name    = c.__name__,
                    module  = c.__module__,
                    values  = fp.get_values(k),
                    outcast = fp.get_outcast(k)
                ))
        return attrmap

    def show_map(self, only=None):
        """
        Show the complete set of attributes that could be found in classes
        collected by the current collector, documented with ``values``
        or ``outcast`` sets if present.
        """
        indent = ' ' * 3
        attrmap = self.build_attrmap(only=only)
        for a in sorted(attrmap.keys()):
            print '*', a, ':'
            for info in sorted(attrmap[a], key=lambda x: x['name']):
                print ' ' * 3, info['name'].ljust(24), '+', info['module']
                for k in [ x for x in info.keys() if x not in ('name', 'module') and info[x] ]:
                    print ' ' * 28, '|', k, '=', info[k]
            print

    def get_values(self, attrname):
        """Complete set of values which are explicitly authorized for a given attribute."""
        allvalues = set()
        for c in self:
            fp = c.retrieve_footprint()
            if attrname in fp.attr:
                for v in fp.get_values(attrname):
                    allvalues.add(v)
        return sorted(allvalues)

    def report_dump(self, stamp=False):
        """Print a nicelly formatted dump report as a dict."""
        self.report_log.fulldump(stamp=stamp)

    @property
    def report_last(self):
        """
        Return the subpart of the report related to the last sequence
        of evaluation through the current collector.
        """
        return self.report_log.last

    def report_sorted(self, **kw):
        """
        Return the subpart of the report related to the last sequence
        of evaluation through the current collector ordered by args.
        """
        return self.report_last.as_tree(**kw)

    def report_dumplast(self):
        """Print a nicelly formatted dump report as a dict."""
        print dump.fulldump(self.report_last.as_dict())

    def report_whynot(self, classname):
        """
        Report why any class mathching the ``classname`` pattern
        had not been selected through the last evaluation.
        """
        return self.report_log.whynot(classname)