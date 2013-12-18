#!/bin/env python
# -*- coding: utf-8 -*-

"""
Fabric for objects with parametrable footprints, i.e. the set of keys/values
that attributes (possibly optionals) could cover.
"""

#: No automatic export
__all__ = []

import copy, re
import inspect
import types

import logging
logging.basicConfig(
    format='[%(asctime)s][%(name)s][%(levelname)s]: %(message)s',
    datefmt='%Y/%d/%m-%H:%M:%S',
    level=logging.WARNING
)
logger = logging.getLogger('footprints')

import dump, observers, priorities, reporting, util

UNKNOWN = '__unknown__'
replattr = re.compile(r'\[(\w+)(?:\:+(\w+))?\]')


class FootprintMaxIter(Exception):
    pass

class FootprintUnreachableAttr(Exception):
    pass

class FootprintFatalError(Exception):
    pass

class FootprintInvalidDefinition(Exception):
    pass

def set_before(priorityref, *args):
    """Set `args` priority before specified `priorityref'."""
    for newpriority in args:
        priorities.top.insert(tag=newpriority, before=priorityref)

def set_after(priorityref, *args):
    """Set `args` priority after specified `priorityref'."""
    for newpriority in reversed(args):
        priorities.top.insert(tag=newpriority, after=priorityref)

class FootprintSetup(object):
    """Defines some defaults and external tools."""

    def __init__(self,
        docstring=False, fatal=True, fastmode=False, fastkeys=('kind',),
        extended=False, dumper=None, report=True, nullreport=reporting.NullReport()
    ):
        """Initialisation of a simple footprint setup driver."""
        if dumper is None:
            self.dumper = dump.Dumper()
        else:
            self.dumper = dumper
        self._extended  = bool(extended)
        self.docstring  = bool(docstring)
        self.fatal      = bool(fatal)
        self.report     = bool(report)
        self.nullreport = nullreport
        self.fastmode   = bool(fastmode)
        self.fastkeys   = tuple(fastkeys)
        self.callback   = None
        self.populset   = set()
        self._defaults  = util.LowerCaseDict()

    def popul(self, obj, clear=False):
        """Populate the ``obj`` with references to active collectors and load methods."""
        if inspect.ismodule(obj) or (isinstance(obj, object) and not inspect.isclass(obj)):
            self.populset.add(obj)
            for k, v in collectorsmap().items():
                if clear or not hasattr(obj, k):
                    setattr(obj, k, v.load)
                if clear or not hasattr(obj, k+'s'):
                    setattr(obj, k+'s', v)
        else:
            logger.error('Could not populate a non-module or non-instance object: %s', obj)
            raise ValueError('Not a module nor an object instance: %s', obj)


    def get_defaults(self):
        """Property getter for footprints defaults."""
        return self._defaults

    def set_defaults(self, *args, **kw):
        """Property setter for current defaults environnement of the footprint resolution."""
        self._defaults = util.LowerCaseDict()
        self._defaults.update(*args, **kw)

    defaults = property(get_defaults, set_defaults)

    def print_defaults(self, ljust=24):
        """Dump the actual values of the default environment."""
        for k in sorted(self._defaults.keys()):
            print k.ljust(ljust), self._defaults[k]

    def get_extended(self):
        """Property getter to ``extended`` switch."""
        return self._extended

    def set_extended(self, switch):
        """Property setter to ``extended`` mode for footprint defaults."""
        if switch is not None:
            self._extended = bool(switch)

    extended = property(get_extended, set_extended)

    def extras(self):
        if self.callback:
            cb = self.callback
            return cb()
        else:
            return dict()

setup = FootprintSetup()

class Collector(util.Catalog):
    """
    A class collector is devoted to the gathering of class references that inherit
    from a given class (here a class with a footprint), according to some other optional criteria.
    """

    def __init__(self, **kw):
        logger.debug('Footprints collector init %s', self)
        self.entry = 'garbage'
        self.instances = util.Catalog(weak=True)
        self.register = True
        self.report = True
        self.autoreport = True
        self.tagreport = None
        self.altreport = False
        super(Collector, self).__init__(**kw)
        if self.tagreport is None:
            self.tagreport = 'footprint-' + self.entry
        self.logreport = reporting.report(self.tagreport)
        for obj in setup.populset:
            setattr(obj, self.entry, self.load)
            setattr(obj, self.entry+'s', self)

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

    def pickup_attributes(self, desc):
        """Try to pickup inside the collector a item that could match the description."""
        logger.debug('Pick up a "%s" in description %s with collector %s', self.entry, desc, self)
        mkreport = desc.pop('report', self.autoreport)
        mkaltreport = desc.pop('altreport', self.altreport)
        if self.entry in desc and desc[self.entry] is not None:
            logger.debug('A %s is already defined %s', self.entry, desc[self.entry])
        else:
            desc[self.entry] = self.find_best(desc)
        if desc[self.entry] is not None:
            desc = desc[self.entry].cleanup(desc)
        else:
            logger.warning('No %s found in description %s', self.entry, "\n" + setup.dumper.cleandump(desc))
            if mkreport and self.report:
                print "\n", self.logreport.info()
                self.lastreport.lightdump()
                if mkaltreport:
                    altreport = self.lastreport.as_flat()
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
            self.logreport.add(collector=self)
        for item in self._items:
            resolved, u_input = item.couldbe(desc, report=self.logreport)
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
            self.logreport.add(collector=self)
        for item in self._items:
            resolved, theinput = item.couldbe(desc, report=self.logreport)
            if resolved: found.append((item, resolved, theinput))
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
            logger.warning('Multiple %s candidates for %s', self.entry, "\n" + setup.dumper.cleandump(desc))
            candidates.sort(key=lambda x: x[0].weightsort(x[2]), reverse=True)
            for i, c in enumerate(candidates):
                thisclass, u_resolved, theinput = c
                logger.warning('  no.%d in.%d is %s', i+1, len(theinput), thisclass)
        topcl, topr, u_topinput = candidates[0]
        return topcl(topr, checked=True)

    def pickup(self, desc):
        """Proxy to :meth:`pickup_attributes`."""
        return self.pickup_attributes(desc)

    def load(self, **desc):
        """Return the entry entry after pickup_attributes."""
        return self.pickup(desc).get(self.entry, None)

    def default(self, **kw):
        """
        Try to find in existing instances tracked by the ``tag`` collector
        a suitable candidate according to description.
        """
        for inst in self.instances():
            if inst.compatible(kw):
                return inst
        return self.load(**kw)

    def dump_report(self, stamp=False):
        """Print a nicelly formatted dump report as a dict."""
        self.logreport.fulldump(stamp=stamp)

    @property
    def lastreport(self):
        """
        Return the subpart of the report related to the last sequence
        of evaluation through the current collector.
        """
        return self.logreport.last

    def sortedreport(self, **kw):
        """
        Return the subpart of the report related to the last sequence
        of evaluation through the current collector ordered by 
        """
        return self.lastreport.as_tree(**kw)

    def dump_lastreport(self, stamp=False):
        """Print a nicelly formatted dump report as a dict."""
        print dump.fulldump(self.lastreport.as_dict())

    def report_why(self, classname):
        """
        Report why the specified any class mathching the ``classname`` pattern
        had not been selected through the last evaluation.
        """
        return self.logreport.whynot(classname)

def collectorsmap(_collectorsmap=dict()):
    """Cached table of collectors currently activated."""
    return _collectorsmap

def collected_footprints():
    """List of current entries collected."""
    return collectorsmap().keys()

def collector(tag='garbage'):
    """Main entry point to get a footprinted classes collector."""
    cmap = collectorsmap()
    tag = tag.rstrip('s')
    if tag not in cmap:
        cmap[tag] = Collector(entry=tag)
    return cmap[tag]

def pickup(rd):
    """Find in current description the attributes that are collected under the ``tag`` name."""
    return collector(rd.pop('tag', 'garbage')).pickup_attributes(rd)

def load(**kw):
    """
    Same as pickup but operates on an expanded dictionary.
    Return either ``None`` or an object compatible with the ``tag``.
    """
    return collector(kw.pop('tag', 'garbage')).load(**kw)

def default(**kw):
    """
    Try to find in existing instances tracked by the ``tag`` collector 
    a suitable candidate according to description.
    """
    return collector(kw.pop('tag', 'garbage')).default(**kw)


class FootprintProxy(object):
    """Access to alive footprint items."""

    def cat(self):
        """Print a list of all existing collectors."""
        for k, v in sorted(collectorsmap().items()):
            print str(len(v)).rjust(4), (k+'s').ljust(16), v

    def catlist(self):
        """Return a list of tuples (len, name, collector) for all alive collectors."""
        return [ (len(v), k+'s', v) for k, v in sorted(collectorsmap().items()) ]

    def objects(self):
        """Print the list of all existing objects tracked by the collectors."""
        for k, c in sorted(collectorsmap().items()):
            objs = c.instances()
            print str(len(objs)).rjust(4), (k+'s').ljust(16), objs

    def objectsmap(self):
        """Return a dictionary of instances sorted by collectors entries."""
        return { k+'s':c.instances() for k, c in collectorsmap().items() }

    def __getattr__(self, attr):
        """Gateway to collector (plural noun) or load method (singular)."""
        if attr.startswith('_'):
            return None
        else:
            if attr.endswith('s'):
                return collector(attr.rstrip('s'))
            else:
                return collector(attr).load

proxy = FootprintProxy()


class Footprint(object):

    def __init__(self, *args, **kw):
        """Initialisation and checking of a given set of footprint."""
        if kw.pop('nodefault', False):
            fp = dict(attr = dict())
        else:
            fp = dict(
                attr = dict(),
                bind = list(),
                info = 'Not documented',
                only = dict(),
                priority = dict(
                    level = priorities.top.TOOLBOX
                )
            )
        for a in args:
            if isinstance(a, dict):
                logger.debug('Init Footprint updated with dict %s', a)
                util.dictmerge(fp, util.list2dict(a, ('attr', 'only')))
            if isinstance(a, Footprint):
                logger.debug('Init Footprint updated with object %s', a)
                util.dictmerge(fp, a.as_dict())
        util.dictmerge(fp, util.list2dict(kw, ('attr', 'only')))
        for a in fp['attr'].keys():
            fp['attr'][a].setdefault('default', None)
            fp['attr'][a].setdefault('optional', False)
            fp['attr'][a]['alias'] = set(fp['attr'][a].get('alias', set()))
            fp['attr'][a]['remap'] = dict(fp['attr'][a].get('remap', dict()))
            fp['attr'][a]['values'] = set(fp['attr'][a].get('values', set()))
            fp['attr'][a]['outcast'] = set(fp['attr'][a].get('outcast', set()))
            ktype = fp['attr'][a].get('type', str)
            kargs = fp['attr'][a].get('args', dict())
            for v in fp['attr'][a]['values']:
                if not isinstance(v, ktype):
                    fp['attr'][a]['values'].remove(v)
                    try:
                        v = ktype(v, **kargs)
                        fp['attr'][a]['values'].add(v)
                        logger.debug('Init Footprint value %s reclassed = %s', a, v)
                    except Exception:
                        logger.error('Bad init footprint value')
                        raise
        self._fp = fp

    def __str__(self):
        return str(self.attr)

    def as_dict(self):
        """
        Returns a deep copy of the internal footprint structure as a pure dictionary.
        Be aware that some objects such as compiled regular expressions remains identical
        through this indeep copy operation.
        """
        return copy.deepcopy(self._fp)

    def as_opts(self):
        """Returns the list of all the possible values as attributes or aliases."""
        opts = list()
        for k in self.attr.keys():
            opts.extend(self.attr[k]['alias'])
        opts.extend(self.attr.keys())
        return set(opts)

    def nice(self):
        """Retruns a nice dump version of the actual footprint."""
        return setup.dumper.cleandump(self._fp)

    def track(self, desc):
        """Returns if the items of ``desc`` are found in the specified footstep ``fp``."""
        fpa = self._fp['attr']
        attrs = fpa.keys()
        aliases = []
        for x in attrs:
            aliases.extend(fpa[x]['alias'])
        return [ a for a in desc if a in attrs or a in aliases ]

    def optional(self, a):
        """Returns either the given attribute ``a`` is optional or not in the current footprint."""
        return self._fp['attr'][a]['optional']

    def mandatory(self):
        """Returns the list of mandatory attributes in the current footprint."""
        fpa = self._fp['attr']
        return [ x for x in fpa.keys() if not fpa[x]['optional'] or fpa[x]['default'] is None ]

    def _firstguess(self, desc):
        """Produces a complete guess of the actual footprint according to actual description ``desc``."""
        guess = dict()
        param = setup.defaults
        inputattr = set()
        for k, kdef in self.attr.iteritems():
            if kdef['optional']:
                if kdef['default'] is None:
                    guess[k] = UNKNOWN
                else:
                    guess[k] = kdef['default']
            else:
                guess[k] = None
            if k in param:
                guess[k] = param[k]
                inputattr.add(k)
            if k in desc:
                guess[k] = desc[k]
                inputattr.add(k)
                logger.debug(' > Attr %s in description : %s', k, desc[k])
            else:
                for a in kdef['alias']:
                    if a in desc:
                        guess[k] = desc[a]
                        inputattr.add(k)
                        break
        return ( guess, inputattr )

    def _findextras(self, desc):
        """
        Return a flat dictionary including ground values as defined by ``setup.extras``
        extended by a dictionary view of any :class:`FootprintBase` object found
        in ``desc`` values.
        """
        extras = setup.extras()
        for vdesc in desc.values():
            if isinstance(vdesc, FootprintBase):
                extras.update(vdesc.puredict())
        if extras:
            logger.debug(' > Extras : %s', extras)
        return extras

    def _addextras(self, extras, guess, more):
        """
        Extend the specified ``extras`` dictionay with pairs of key/value
        suggested in the ``more`` dictionary which are not already defined
        in ``extras`` or the actual ``guess``.
        """
        for k in [ x.lower() for x in more.keys() ]:
            if k not in extras and k not in guess:
                extras[k] = more[k]

    def _replacement(self, nbpass, k, guess, extras, todo):
        """
        Try to resolve any replacement sequence inside the ``guess[k]`` value
        according to actual values in the ``guess`` or ``extras`` current dictionaries.

        A replacement sequence is a list of one or more items in brackets of the form:

          * '[key-name]'
          * '[key-name:attr-name]' or '[key-name::attr-name]'
          * '[key-name:meth-name]' or '[key-name::meth-name]'

        If the ``key-name`` could not be found in actual ``guess`` or ``extras`` dictionaries
        the method raises an :exception:`FootprintUnreachableAttr`.
        """
        if nbpass > 25:
            logger.error('Resolve probably cycling too much... %d tries ?', nbpass)
            raise FootprintMaxIter('Too many Footprint replacements')

        changed = 1
        while changed:
            changed = 0
            mobj = replattr.search(str(guess[k]))
            if mobj:
                replk = mobj.group(1)
                replm = mobj.group(2)
                if replk not in guess and replk not in extras:
                    logger.error('No %s attribute in guess:', replk)
                    logger.error('%s', guess)
                    logger.error('No %s attribute in extras:', replk)
                    logger.error('%s', extras)
                    raise FootprintUnreachableAttr('Could not replace attribute ' + replk)
                if replk in guess:
                    if replk not in todo:
                        changed = 1
                        if replm:
                            subattr = getattr(guess[replk], replm, None)
                            if subattr is None:
                                guess[k] = None
                            else:
                                guess[k] = replattr.sub(str(subattr), guess[k], 1)
                        else:
                            guess[k] = replattr.sub(str(guess[replk]), guess[k], 1)
                elif replk in extras:
                    changed = 1
                    if replm:
                        subattr = getattr(extras[replk], replm, None)
                        if subattr is None:
                            guess[k] = None
                        else:
                            if callable(subattr):
                                try:
                                    attrcall = subattr(guess, extras)
                                except Exception as trouble:
                                    logger.critical(trouble)
                                    attrcall = '__SKIP__'
                                    changed = 0
                                if attrcall is None:
                                    guess[k] = None
                                elif attrcall != '__SKIP__':
                                    guess[k] = replattr.sub(str(attrcall), guess[k], 1)
                            else:
                                guess[k] = replattr.sub(str(subattr), guess[k], 1)
                    else:
                        guess[k] = replattr.sub(str(extras[replk]), guess[k], 1)

        if guess[k] is not None and replattr.search(str(guess[k])):
            logger.debug(' > Requeue resolve < %s > : %s', k, guess[k])
            todo.append(k)
            return False
        else:
            logger.debug(' > No more substitution for %s', k)
            return True

    def in_values(self, item, values):
        """Check that item is inside values or compare to one of these values."""
        if item in values:
            return True
        else:
            return bool([ x for x in values if x == item ])

    def resolve(self, desc, **kw):
        """Try to guess how the given description ``desc`` could possibly match the current footprint."""

        opts = dict(fatal=setup.fatal, fast=setup.fastmode)
        opts.update(kw)
        report = opts.pop('report', False) or setup.nullreport

        guess, attr_input = self._firstguess(desc)
        extras = self._findextras(desc)
        attr_seen = set()

        # Add arguments from current description not yet used to extra parameters
        self._addextras(extras, guess, desc)

        # Add arguments from defaults footprint not already defined to extra parameters
        if setup.extended:
            self._addextras(extras, guess, setup.defaults)

        attrs = self.attr

        if None in guess.values():
            todo = []
        else:
            todo = attrs.keys()
            for kfast in [ x for x in setup.fastkeys if x in todo ]:
                todo.remove(kfast)
                todo.insert(0, kfast)

        nbpass = 0
        diags = dict()

        while todo:

            k = todo.pop(0)
            kdef = attrs[k]
            nbpass += 1
            if not self._replacement(nbpass, k, guess, extras, todo) or guess[k] is None: continue

            attr_seen.add(k)

            while kdef['remap'].has_key(guess[k]):
                logger.debug(' > Attr %s remap(%s) = %s', k, guess[k], kdef['remap'][guess[k]])
                guess[k] = kdef['remap'][guess[k]]

            if guess[k] is UNKNOWN:
                logger.debug(' > Optional attr still unknown : %s', k)
            else:
                ktype = kdef.get('type', str)
                if kdef.get('isclass', False):
                    if not issubclass(guess[k], ktype):
                        logger.debug(' > Attr %s class %s not a subclass %s', k, guess[k], ktype)
                        report.add(attribute=k, why=reporting.REPORT_WHY_SUBCLASS, args=ktype.__name__)
                        diags[k] = True
                        guess[k] = None
                elif not isinstance(guess[k], ktype):
                    logger.debug(' > Attr %s reclass(%s) as %s', k, guess[k], ktype)
                    kargs = kdef.get('args', dict())
                    try:
                        guess[k] = ktype(guess[k], **kargs)
                        logger.debug(' > Attr %s reclassed = %s', k, guess[k])
                    except Exception:
                        logger.debug(' > Attr %s badly reclassed as %s = %s', k, ktype, guess[k])
                        report.add(attribute=k, why=reporting.REPORT_WHY_RECLASS, args=(ktype.__name__, str(guess[k])))
                        diags[k] = True
                        guess[k] = None
                if kdef['values'] and not self.in_values(guess[k], kdef['values']):
                    logger.debug(' > Attr %s value not in range = %s %s', k, guess[k], kdef['values'])
                    report.add(attribute=k, why=reporting.REPORT_WHY_OUTSIDE, args=guess[k])
                    diags[k] = True
                    guess[k] = None
                if kdef['outcast'] and guess[k] in kdef['outcast']:
                    logger.debug(' > Attr %s value excluded from range = %s %s', k, guess[k], kdef['outcast'])
                    report.add(attribute=k, why=reporting.REPORT_WHY_OUTCAST, args=guess[k])
                    diags[k] = True
                    guess[k] = None

            if guess[k] is None and ( opts['fast'] or k in setup.fastkeys ):
                logger.debug(' > Fast exit from resolve on key "%s"', k)
                break

        for k in attrs.keys():
            if guess[k] == 'None':
                guess[k] = None
                logger.warning(' > Attr %s is a null string', k)
                if k not in diags:
                    report.add(attribute=k, why=reporting.REPORT_WHY_INVALID)
            if guess[k] is None:
                attr_input.discard(k)
                if k not in diags:
                    report.add(attribute=k, why=reporting.REPORT_WHY_MISSING)
                if opts['fatal']:
                    logger.critical('No valid attribute %s', k)
                    raise FootprintFatalError('No attribute `' + k + '` is fatal')
                else:
                    logger.debug(' > No valid attribute %s', k)

        return ( guess, attr_input, attr_seen )

    def checkonly(self, rd, report=setup.nullreport):
        """Be sure that the resolved description also match at least one item per ``only`` feature."""

        params = setup.defaults
        for k, v in self.only.items():
            if not hasattr(v, '__iter__'):
                v = (v, )

            actualattr = k
            after, before = False, False
            if k.startswith('after_'):
                after = True
            if k.startswith('before_'):
                before = True
            if after or before:
                actualattr = k.partition('_')[-1]

            actualvalue = rd.get(actualattr, params.get(actualattr.lower(), None))
            if actualvalue is None:
                rd = False
                report.add(attribute=actualattr, only=reporting.REPORT_ONLY_NOTFOUND, args=k)
                break

            checkflag = False
            for checkvalue in v:
                if after:
                    checkflag = checkflag or bool(actualvalue >= checkvalue)
                elif before:
                    checkflag = checkflag or bool(actualvalue < checkvalue)
                elif hasattr(checkvalue, 'match'):
                    checkflag = checkflag or bool(checkvalue.match(actualvalue))
                else:
                    checkflag = checkflag or not bool(cmp(actualvalue, checkvalue))

            if not checkflag:
                rd = False
                if report:
                    report.add(attribute=actualattr, only=reporting.REPORT_ONLY_NOTMATCH, args=v)
                break

        return rd

    @property
    def info(self):
        """Read-only property. Direct access to internal footprint informative description."""
        return self._fp['info']

    @property
    def attr(self):
        """Read-only property. Direct access to internal footprint set of attributes."""
        return self._fp['attr']

    @property
    def bind(self):
        """Read-only property. Direct access to internal footprint binding between attributes."""
        return self._fp['bind']

    @property
    def only(self):
        """Read-only property. Direct access to internal footprint restrictions rules."""
        return self._fp['only']

    @property
    def priority(self):
        """Read-only property. Direct access to internal footprint priority rules."""
        return self._fp['priority']


class FootprintAttrAccess(object):
    """Accessor class to footprint attributes."""

    def __init__(self, attr, doc='Undocumented footprint attribute'):
        self.attr = attr
        self.__doc__ = doc

    def __get__(self, instance, owner):
        thisattr = instance._attributes.get(self.attr, None)
        if thisattr is UNKNOWN: thisattr = None
        return thisattr

    def __set__(self, instance, value):
        raise AttributeError, 'This attribute should not be overwritten'

    def __delete__(self, instance):
        raise AttributeError, 'This attribute should not be deleted'


class FootprintBaseMeta(type):
    """
    Meta class constructor for :class:`FootprintBase`.
    The current :data:`_footprint` data which could be a simple dict
    or a :class:`Footprint` object is used to instantiate a new :class:`Footprint`,
    built as a merge of the footprint of the base classes.
    """

    def __new__(cls, n, b, d):
        logger.debug('Base class for footprint usage "%s / %s", bc = ( %s ), internal = %s', cls, n, b, d)
        fplocal  = d.get('_footprint', dict())
        abstract = d.setdefault('_abstract', False)
        bcfp = [ c.__dict__.get('_footprint', dict()) for c in b ]
        if type(fplocal) is types.ListType:
            bcfp.extend(fplocal)
        else:
            bcfp.append(fplocal)
        d['_footprint'] = Footprint( *bcfp )
        for k in d['_footprint'].attr.keys():
            d[k] = FootprintAttrAccess(k)
        realcls = super(FootprintBaseMeta, cls).__new__(cls, n, b, d)
        if not abstract:
            if realcls._explicit and not realcls.mandatory():
                raise FootprintInvalidDefinition('Explicit class without any mandatory footprint attribute.')
            for cname in realcls._collector:
                thiscollector = collector(cname)
                thiscollector.add(realcls)
                if thiscollector.register:
                    observers.getbyname(realcls.fullname()).register(thiscollector)
            logger.debug('Register class %s in collector %s (%s)', realcls, thiscollector, cname)
        basedoc = realcls.__doc__
        if not basedoc:
            basedoc = 'Not documented yet.'
        realcls.__doc__ = basedoc
        if setup.docstring:
            realcls.__doc__ += "\n\n    Footprint::\n\n" + realcls.footprint().nice()

        return realcls


class FootprintBase(object):
    """
    Base class for any other thematic class that would need to incorporate a :class:`Footprint`.
    Its metaclass is :class:`FootprintBaseMeta`.
    """

    __metaclass__ = FootprintBaseMeta

    _abstract  = True
    _explicit  = True
    _collector = ('garbage',)

    def __init__(self, *args, **kw):
        logger.debug('Abstract %s init', self.__class__)
        if self.__class__._abstract:
            raise FootprintInvalidDefinition('Could not instanciate abstract class.')
        checked = kw.pop('checked', False)
        self._instfp = Footprint(self._footprint.as_dict())
        self._attributes = dict()
        for a in args:
            logger.debug('FootprintBase %s arg %s', self, a)
            if isinstance(a, dict):
                self._attributes.update(a)
        self._attributes.update(kw)
        if not checked:
            logger.debug('Resolve attributes at footprint init %s', object.__repr__(self))
            self._attributes, u_attr_input, u_attr_seen = self._instfp.resolve(self._attributes, fatal=True)
        self._observer = observers.getbyname(self.__class__.fullname())
        self.make_alive()

    @property
    def realkind(self):
        """Must be implemented by subclasses."""
        pass

    def make_alive(self):
        """Thnigs to do after new or init construction."""
        self._observer.notify_new(self, dict())

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['_observer']
        return d

    def __setstate__(self, state):
        self._observer = observers.getbyname(self.__class__.fullname())
        self.make_alive()

    def __del__(self):
        try:
            self._observer.notify_del(self, dict())
        except (TypeError, AttributeError):
            logger.debug('Too late for notify_del')

    @classmethod
    def is_abstract(cls):
        """Returns either the current class could be instanciated or not."""
        return cls._abstract

    @classmethod
    def fullname(cls):
        """Returns a nicely formated name of the current class (dump usage)."""
        return '{0:s}.{1:s}'.format(cls.__module__, cls.__name__)

    def shortname(self):
        """Returns the short name of the object's class."""
        return self.__class__.__name__

    def attributes(self):
        """Returns the list of current attributes."""
        return self._attributes.keys()

    def puredict(self):
        """Returns a shallow copy of the current attributes."""
        pure = dict()
        for k in self._attributes.keys():
            pure[k] = getattr(self, k)
        return pure

    def shellexport(self):
        """See the current footprint as a pure dictionary when exported."""
        return self.puredict()

    def _str_more(self):
        """Additional information to be combined in repr output."""
        return 'footprint=' + str(len(self.attributes()))

    def __str__(self):
        """
        Basic layout for nicely formatted print, built as the concatenation
        of the class full name and some :meth:`addrepr` additional information.
        """
        return '{0:s} | {1:s}>'.format(repr(self).rstrip('>'), self._str_more())

    @property
    def info(self):
        """Information from the current footprint."""
        return self.footprint().info

    @classmethod
    def footprint(selfcls, **kw):
        """Returns the internal checked ``footprint`` of the current object."""
        fpk = '_footprint'
        if '_instfp' in selfcls.__dict__:
            fpk = '_instfp'
        if len(kw):
            logger.debug('Extend %s footprint %s', selfcls, kw)
            selfcls.__dict__[fpk] = Footprint(selfcls.__dict__[fpk], kw)
        return selfcls.__dict__[fpk]

    @classmethod
    def mandatory(cls):
        """
        Returns the attributes that should be present in a description
        in order to be able to match the current object.
        """
        return cls.footprint().mandatory()

    @classmethod
    def optional(cls, a):
        """Returns either the specified attribute ``a`` is optional or not."""
        return cls.footprint().optional(a)

    @classmethod
    def couldbe(cls, rd, report=None, mkreport=False):
        """
        This is the heart of any selection purpose, particularly in relation
        with the :meth:`find_all` mechanism of :class:`footprints.Collector` classes.
        It returns the *resolved* form in which the current ``rd`` description
        could be recognized as a footprint of the current class, :data:`False` otherwise.
        """
        logger.debug('-' * 180)
        logger.debug('Couldbe a %s ?', cls)
        if mkreport and not report:
            report = reporting.report('void')
            report.add(collector=proxy.garbages)
        if report:
            report.add(candidate=cls)
        fp = cls.footprint()
        resolved, attr_input, u_attr_seen = fp.resolve(rd, fatal=False, report=report)
        if resolved and None not in resolved.values():
            return ( fp.checkonly(resolved, report), attr_input )
        else:
            if mkreport:
                report.last.lightdump()
            return ( False, attr_input )

    def compatible(self, rd):
        """
        Resolve a subset of a description according to my footprint,
        and then compare to my actual values.
        """
        fp = self.footprint()
        resolved, u_inputattr = fp.resolve(rd, fatal=False, fast=False, report=None)
        rc = True
        for k in rd.keys():
            if resolved[k] is None or self._attributes[k] != resolved[k]:
                rc = False
        return rc

    def cleanup(self, rd):
        """
        Removes in the specified ``rd`` description the keys that are
        tracked as part of the footprint of the current object.
        """
        fp = self.footprint()
        for attr in fp.track(rd):
            logger.debug('Removing attribute %s : %s', attr, rd[attr])
            del rd[attr]
        return rd

    @classmethod
    def weightsort(cls, realinputs):
        """Tuple with ordered weights to make a choice possible between various electible footprints."""
        fp = cls.footprint()
        return ( fp.priority['level'].rank, realinputs )

    @classmethod
    def authvalues(cls, attrname):
        """Return the list of authorized values of a footprint attribute (if any)."""
        return list(cls.footprint().attr[attrname]['values'])
