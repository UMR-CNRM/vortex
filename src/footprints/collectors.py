"""
Handling of footprints collectors.
Module's usage is mostly dedicated to the main footprints package.
The footprints proxy could make some part of the interface visible as well.
"""

from weakref import WeakSet
import collections
import logging

from bronx.fancies import dump, loggers
from bronx.stdtypes.catalog import Catalog
from bronx.patterns import observer, getbytag

from . import config, priorities, reporting

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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

class Collector(getbytag.GetByTag, Catalog, observer.Observer):
    """
    A class collector is devoted to the gathering of class references that inherit
    from a given class (here a class with a footprint), according to some other optional criteria.

    :param int non_ambiguous_loglevel: The loglevel used in the find_best method when
        several choices are possible but the priority of the various candidates
        makes the choice easy (default: logging.INFO).
    """

    _tag_default = 'garbage'

    def __init__(self, **kw):
        logger.debug('Footprints collector init %s', str(self))
        self.instances = Catalog(weak=True)
        self.abstract_classes = Catalog(weak=True)
        self.register = True
        self.report = config.ONERROR_REPORTING
        self.lreport_len = config.DFLT_MAXLEN_LIGHT_REPORTING
        self.report_auto = True
        self.report_tag = None
        self.report_style = config.RAW_REPORTINGSTYLE
        self.non_ambiguous_loglevel = logging.INFO
        getbytag.GetByTag.__init__(self)
        Catalog.__init__(self, **kw)
        if self.report_tag is None:
            self.report_tag = 'footprint-' + self.tag
        r_maxlen = None if self.report == config.FULL_REPORTING else self.lreport_len
        self.report_log = reporting.get(tag=self.report_tag, log_maxlen=r_maxlen)
        config.add2proxies(self)
        self._del_fasttrack()

    @classmethod
    def tag_clean(cls, tag):
        """Return a lower-case string without any "s" at the end."""
        return tag.lower().rstrip('s')

    def newobsitem(self, item, info):
        """Register a new instance of some of the classes in the current collector."""
        logger.debug('Notified {!r} new item {!r}'.format(self, item))
        self.instances.add(item)

    def delobsitem(self, item, info):
        """Unregister an existing object in the current collector of instances."""
        logger.debug('Notified {!r} del item {!r}'.format(self, item))
        self.instances.discard(item)

    def filter_package(self, packname):
        """Find in current collector classes with name starting with ``packname``."""
        return [cl for cl in self.items() if cl.fullname().startswith(packname)]

    def discard_package(self, packname, verbose=True):
        """Discard from current collector classes with name starting with ``packname``."""
        for x in self.filter_package(packname):
            if verbose:
                print('Bye...', x)
            self.discard(x)

    def filter_onflag(self, flagmethod, default=True):
        """Find in current collector classes with method ``flagmethod`` returning ``default``."""
        return [cl for cl in self.items() if hasattr(cl, flagmethod) and getattr(cl, flagmethod)() == default]

    def discard_onflag(self, flagmethod, default=True, verbose=True):
        """Discard from current collector classes with method ``flagmethod`` returning ``default``."""
        for x in self.filter_onflag(flagmethod, default):
            if verbose:
                print('Bye...', x)
            self.discard(x)

    def filter_higher_level(self, tag):
        """Find in current collector classes with priority level higher or equal to ``level``."""
        plevel = priorities.top.level(tag)
        return [cl for cl in self.items() if cl.footprint_pl() >= plevel]

    def discard_higher_level(self, tag, verbose=True):
        """Discard from current collector classes with priority level higher or equal to ``level``."""
        for x in self.filter_higher_level(tag):
            if verbose:
                print('Bye...', x)
            self.discard(x)

    def filter_lower_level(self, tag):
        """Find in current collector classes with priority level lower than ``level``."""
        plevel = priorities.top.level(tag)
        return [cl for cl in self.items() if cl.footprint_pl() < plevel]

    def discard_lower_level(self, tag, verbose=True):
        """Discard from current collector classes with priority level lower than ``level``."""
        for x in self.filter_lower_level(tag):
            if verbose:
                print('Bye...', x)
            self.discard(x)

    def reset_package_level(self, packname, tag):
        """Reset priority level current collector classes with name starting with ``packname``."""
        plevel = priorities.top.level(tag)
        for cl in self.filter_package(packname):
            fp = cl.footprint_retrieve()
            fp.priority['level'] = plevel

    def _upd_fasttrack_index(self, cls):
        attrerror = set()
        for myattr in self._fasttrack_attr:
            myfp = cls.footprint_retrieve()
            if myattr in myfp.mandatory():
                myvalues = myfp.get_values(myattr)
                # Is there some restrictions on values ?
                if myvalues:
                    # Ensure that the attribute types are consistent
                    if self._fasttrack_type[myattr] is None:
                        self._fasttrack_type[myattr] = myfp.attr[myattr].get('type', str)
                        self._fasttrack_typeargs[myattr] = myfp.attr[myattr].get('args', dict())
                    else:
                        if not (self._fasttrack_type[myattr] is myfp.attr[myattr].get('type', str) and
                                self._fasttrack_typeargs[myattr] == myfp.attr[myattr].get('args', dict())):
                            logger.warning("Inconsistent types (%s vs %s) for fasttrack attributes (class: %s). " +
                                           "Removing it (%s) from the fasttrack list.",
                                           str(self._fasttrack_type[myattr]),
                                           str(myfp.attr[myattr].get('type', str)),
                                           repr(cls), myattr)
                            attrerror.add(myattr)
                            continue
                    # Let's go...
                    for myvalue in myvalues:
                        self._fasttrack_index[myattr][myvalue].add(cls)

                # No restrictions on values so it's a potential candidate for everyone
                else:
                    self._fasttrack_trap[myattr].add(cls)

            # The attribute is optional or missing so it's a possible candidate for everyone
            else:
                self._fasttrack_trap[myattr].add(cls)

        # Process errors
        if attrerror:
            for myattr in set(self._fasttrack_attr):
                if myattr in attrerror:
                    self._fasttrack_attr.remove(myattr)
                    del self._fasttrack_type[myattr]
                    del self._fasttrack_typeargs[myattr]
                    del self._fasttrack_index[myattr]
                    del self._fasttrack_trap[myattr]

    def _upd_fasttrack_delete(self, cls):
        for fvalues in self._fasttrack_index.values():
            for classes in fvalues.values():
                classes.discard(cls)
        for classes in self._fasttrack_trap.values():
            classes.discard(cls)

    def _del_fasttrack(self):
        self._fasttrack_attr = set()
        self._fasttrack_index = dict()
        self._fasttrack_type = dict()
        self._fasttrack_typeargs = dict()
        self._fasttrack_trap = dict()

    def _set_fasttrack(self, attrset):
        self._del_fasttrack()
        self._fasttrack_attr = set(attrset)
        for myattr in self._fasttrack_attr:
            self._fasttrack_type[myattr] = None
            self._fasttrack_typeargs[myattr] = dict()
            self._fasttrack_index[myattr] = collections.defaultdict(WeakSet)
            self._fasttrack_trap[myattr] = WeakSet()
        for mycls in self._items:
            self._upd_fasttrack_index(mycls)

    def _get_fasttrack(self):
        return set(self._fasttrack_attr)

    fasttrack = property(_get_fasttrack, _set_fasttrack)

    def _fasttrack_subsetting(self, desc):
        if self._fasttrack_attr:
            objgroup_list = list()
            for k, v in desc.items():
                if k in self._fasttrack_attr:
                    # Check if the key's value is in the index
                    if v in self._fasttrack_index[k]:
                        indexkey = v
                    else:
                        # A type conversion might be usefull
                        try:
                            v_conv = self._fasttrack_type[k](v, ** self._fasttrack_typeargs[k])
                        except (ValueError, TypeError):
                            v_conv = None
                        if v_conv is not None and v_conv in self._fasttrack_index[k]:
                            indexkey = v_conv
                        else:
                            # Ok we give up...
                            indexkey = None

                    if indexkey is not None:
                        logger.debug('Fasttrack subsetting took place for key %s', k)
                        objgroup_list.append(self._fasttrack_index[k][indexkey] |
                                             self._fasttrack_trap[k])
            if objgroup_list:
                if len(objgroup_list) > 1:
                    finalset = objgroup_list[0]
                    for objgroup in objgroup_list[1:]:
                        finalset = finalset.intersection(objgroup)
                    return finalset
                else:
                    return objgroup_list[0]

        return self._items

    def add(self, *items, **kwargs):
        """Add the ``items`` entries in the current catalog."""
        if kwargs.get('abstract', False):
            self.abstract_classes.add(*items)
        else:
            super().add(*items)
            for item in items:
                self._upd_fasttrack_index(item)

    def discard(self, bye):
        """Remove the ``bye`` entry from current catalog."""
        super().discard(bye)
        self._upd_fasttrack_delete(bye)

    def pickup_and_cache(self, desc, resolvecache=None):
        """Try to pickup inside the collector an item that could match the description."""
        logger.debug('Pick up a "{:s}" in description {!s} with collector {!r}'.format(self.tag, desc, self))
        if resolvecache is None:
            resolvecache = ResolveCache()
        emptywarning = desc.pop('_emptywarning', True)
        mkstdreport = desc.pop('_report', self.report_auto)
        reportstyle = desc.pop('_report_style', self.report_style)
        for hidden in [x for x in desc.keys() if x.startswith('_')]:
            logger.warning('Hidden argument "%s" ignored in pickup attributes', hidden)
            del desc[hidden]
        if self.tag in desc and desc[self.tag] is not None:
            logger.debug('A %s is already defined %s', self.tag, str(desc[self.tag]))
        else:
            desc[self.tag] = self.find_best(desc, resolvecache=resolvecache)
        if desc[self.tag] is not None:
            desc = desc[self.tag].footprint_cleanup(desc)
        elif emptywarning:
            dumper = dump.get()
            logger.warning("No %s found in description \n%s", self.tag, dumper.cleandump(desc))
            if mkstdreport and self.report:
                print("\n", self.report_log.info(), "\n")
                if reportstyle == config.RAW_REPORTINGSTYLE:
                    self.report_last.lightdump()
                if reportstyle == config.FLAT_REPORTINGSTYLE:
                    altreport = self.report_last.as_flat()
                    altreport.reshuffle(['why', 'attribute'], skip=False)
                    altreport.fulldump()
                    altreport.reshuffle(['only', 'attribute'], skip=False)
                    altreport.fulldump()
                if reportstyle == config.FACTORIZED1_REPORTINGSTYLE:
                    altreport = self.report_sorted()
                    altreport.orderedprint()
                if reportstyle == config.FACTORIZED2_REPORTINGSTYLE:
                    altreport = self.report_sorted()
                    altreport.dumper()
        return desc, resolvecache

    def pickup(self, desc, resolvecache=None):
        """Try to pickup inside the collector an item that could match the description."""
        return self.pickup_and_cache(desc, resolvecache=resolvecache)[0]

    def find_any(self, desc, resolvecache=None):
        """
        Return the first item of the collector that :meth:`footprint_couldbe`
        as described by argument ``desc``.
        """
        logger.debug('Search any %s in collector %s', str(desc), str(self._items))
        if resolvecache is None:
            resolvecache = ResolveCache()
        requeue = True
        report_log = None if self.report == config.ONERROR_REPORTING else self.report_log
        while requeue:
            requeue = False
            if self.report and report_log is not None:
                report_log.add(collector=self)
            for item in self._fasttrack_subsetting(desc):
                resolved, u_input = item.footprint_couldbe(desc,  # @UnusedVariable
                                                           resolvecache=resolvecache,
                                                           report=report_log)
                if resolved:
                    return item(resolved, checked=True)
            if (self.report == config.ONERROR_REPORTING and
                    report_log is None):
                requeue = True
                report_log = self.report_log
        return None

    def find_all(self, desc, resolvecache=None):
        """
        Returns all the items of the collector that :meth:`footprint_couldbe`
        as described by argument ``desc``.
        """
        logger.debug('Search all %s in collector %s', str(desc), str(self._items))
        if resolvecache is None:
            resolvecache = ResolveCache()
        requeue = True
        report_log = None if self.report == config.ONERROR_REPORTING else self.report_log
        while requeue:
            requeue = False
            found = list()
            if self.report and report_log is not None:
                report_log.add(collector=self)
            for item in self._fasttrack_subsetting(desc):
                resolved, theinput = item.footprint_couldbe(desc,
                                                            resolvecache=resolvecache,
                                                            report=report_log)
                if resolved:
                    found.append((item, resolved, theinput))
            if (not found and
                    self.report == config.ONERROR_REPORTING and
                    report_log is None):
                requeue = True
                report_log = self.report_log
        return found

    def find_best(self, desc, resolvecache=None):
        """
        Returns the best of the items returned by the :meth:`find_all` method
        according to potential priority rules.
        """
        logger.debug('Search best %s in collector %s', str(desc), str(self._items))
        candidates = self.find_all(desc, resolvecache=resolvecache)
        if not candidates:
            return None
        if len(candidates) > 1:
            candidates.sort(key=lambda x: x[0].footprint_weight(len(x[2])), reverse=True)
            ambiguous = candidates[0][0].footprint_pl() == candidates[1][0].footprint_pl()
            loglevel = logging.WARNING if ambiguous else self.non_ambiguous_loglevel
            dumper = dump.get()
            logger.log(loglevel, "Multiple %s candidates \n%s", self.tag, dumper.cleandump(desc))
            for i, c in enumerate(candidates):
                thisclass, u_resolved, theinput = c  # @UnusedVariable
                logger.log(loglevel, 'no.%d in.%d is %s', i + 1, len(theinput), str(thisclass))
        topcl, topr, u_topinput = candidates[0]  # @UnusedVariable
        return topcl(topr, checked=True)

    def load(self, **desc):
        """Return the value matching current collector's tag after pickup of attributes."""
        return self.pickup(desc).get(self.tag, None)

    def almost_clone(self, original, **extra):
        """Return an almost clone, with some extra or different attributes."""
        assert hasattr(original, 'footprint_as_dict')
        attrs = original.footprint_as_dict()
        attrs.update(extra)
        return self.load(**attrs)

    def default(self, **kw):
        """
        Try to find in existing instances tracked by the ``tag`` collector
        a suitable candidate according to description.
        """
        for inst in self.instances():
            if inst.footprint_reusable() and inst.footprint_compatible(kw):
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
            fp = c.footprint_retrieve()
            for k in [ka for ka in fp.attr.keys() if only is None or ka in only]:
                opt = ' [optional]' if fp.optional(k) else ''
                alist = attrmap.setdefault(k + opt, list())
                alist.append(dict(
                    name=c.__name__,
                    module=c.__module__,
                    values=fp.get_values(k),
                    outcast=fp.get_outcast(k)
                ))
        return attrmap

    def show_attrmap(self, only=None):
        """
        Show the complete set of attributes that could be found in classes
        collected by the current collector, documented with ``values``
        or ``outcast`` sets if present.
        """
        attrmap = self.build_attrmap(only=only)
        for a in sorted(attrmap.keys()):
            print(' *', a + ':')
            for info in sorted(attrmap[a], key=lambda x: x['name']):
                print(' ' * 4, info['name'].ljust(22), '+', info['module'])
                for k in [x for x in info.keys() if x not in ('name', 'module') and info[x]]:
                    print(' ' * 29, '|', k, '=',
                          str(info[k]).replace("'", '').replace('(', '').replace(')', '').strip(','))
            print()

    def show_attrkeys(self, only=None):
        """
        Show the list of attribute names that could be found in classes
        collected by the current collector.
        """
        attrmap = self.build_attrmap(only=only)
        for a in [x.split() + [''] for x in sorted(attrmap.keys())]:
            print(' *', a[0].ljust(24), a[1])

    def get_values(self, attrname):
        """Complete set of values which are explicitly authorized for a given attribute."""
        allvalues = set()
        for c in self:
            fp = c.footprint_retrieve()
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
        """Print a nicely formatted dump report as a dict."""
        print(dump.fulldump(self.report_last.as_dict()))

    def report_whynot(self, classname):
        """
        Report why any class matching the ``classname`` pattern
        has not been selected through the last evaluation.
        """
        return self.report_log.whynot(classname)


# Utility classes that cache some results in order to speed-up the resolution
class ResolveCache:

    def __init__(self):
        setup = config.get()
        self.defaults = setup.defaults
        self.extras = setup.extras()
        self._shallow_cache = dict()

    def get_shallow_fp(self, obj):
        if obj not in self._shallow_cache:
            self._shallow_cache[obj] = obj.footprint_as_shallow_dict()
        return self._shallow_cache[obj]
