"""
A generic multi-purpose fabric for objects with tunable footprints,
i.e. some set of key/value pairs that attributes (possibly optional) could cover.
"""

import os
import re
import copy
import types
import weakref
import collections

from bronx.fancies import dump, loggers
from bronx.patterns import observer

from . import access, collectors, config, doc
from . import priorities, proxies, reporting, util
from .stdtypes import FPDict, FPList, FPRegex, FPSet, FPTuple

assert FPDict
assert FPList
assert FPRegex
assert FPSet
assert FPTuple


#: No automatic export

__all__ = []


# Default logging

logger = loggers.getLogger('footprints')


# Default setup

setup = config.get(
    docstrings=int(os.environ.get('FOOTPRINT_DOCSTRINGS', 0)),
    shortnames=int(os.environ.get('FOOTPRINT_SHORTNAMES', 0))
)


# Default proxy

proxy = proxies.get()


# Predefined constants

UNKNOWN = '__unknown__'
replattr = re.compile(r'\[(\w+)(?::+([:\w]+))?(?:#(\w+))?(?:%([^\]]+))?\]')


# Footprint exceptions

class FootprintException(Exception):
    pass


class FootprintMaxIter(FootprintException):
    pass


class FootprintUnreachableAttr(FootprintException):
    pass


class FootprintFatalError(FootprintException):
    pass


class FootprintInvalidDefinition(FootprintException):
    pass


# Module interface

def pickup(rd):
    """Find in current description the attributes that are collected under the ``tag`` name."""
    return collectors.get(tag=rd.pop('tag', 'garbage'),
                          report=setup.report, lreport_len=setup.lreport_len,
                          report_style=setup.report_style).pickup(rd)


def load(**kw):
    """
    Same as pickup but operates on an expanded dictionary.
    Return either ``None`` or an object compatible with the ``tag``.
    """
    return collectors.get(tag=kw.pop('tag', 'garbage'),
                          report=setup.report, lreport_len=setup.lreport_len,
                          report_style=setup.report_style).load(**kw)


def default(**kw):
    """
    Try to find in existing instances tracked by the ``tag`` collector
    a suitable candidate according to description.
    """
    return collectors.get(tag=kw.pop('tag', 'garbage'),
                          report=setup.report, lreport_len=setup.lreport_len,
                          report_style=setup.report_style).default(**kw)


def grep(**kw):
    """Try to find any instance in all collectors that could match given attributes."""
    allgrep = list()
    for c in collectors.values():
        allgrep.extend(c.grep(**kw))
    return allgrep


def collected_classes():
    """Return a set of all collected footprint-based classes."""
    c_classes = list()
    for kv in collectors.values():
        c_classes.extend(kv.items())
    return set(c_classes)


def collected_priorities(tag):
    """Print a table of collected classes with a priority level higher or equal to ``tag``."""
    plevel = priorities.top.level(tag)
    for cl in sorted({c
                      for cv in collectors.values()
                      for c in cv.filter_higher_level(plevel)},
                     key=lambda z: z.fullname()):
        pl = cl.footprint_level()
        print(pl.rjust(10), '-', cl.fullname())


def reset_package_priority(packname, tag):
    """Reset priority level in all collectors for the specified ``package``."""
    for c in collectors.values():
        c.reset_package_level(packname, tag)


# Base classes

class Footprint:
    """
    This class defines the objects in charge of handling the footprint definition itself
    and the resolution mecanism through keys-values description matching.
    """

    def __init__(self, *args, **kw):
        """Initialisation and checking of a given set of footprint."""
        myclsname = kw.pop('myclsname', 'unknown class')
        if kw.pop('nodefault', False):
            fp = dict(attr=dict())
        else:
            fp = dict(
                attr=dict(),
                bind=list(),
                info='Not documented',
                only=dict(),
                priority=dict(
                    level=priorities.top.DEFAULT  # @UndefinedVariable
                )
            )
        typescheck = collections.defaultdict(list)
        for a in args:
            adict = None
            if isinstance(a, dict) and bool(a):
                logger.debug('Init Footprint updated with dict %s', a)
                adict = util.list2dict(a, ('attr', 'only'))
            if isinstance(a, Footprint) and (bool(a.attr) or bool(a.only)):
                logger.debug('Init Footprint updated with object %s', a)
                adict = a.as_dict()
            if adict is not None:
                util.dictmerge(fp, adict)
                if 'attr' in adict:
                    for attr, attrdict in adict['attr'].items():
                        if 'type' in attrdict:
                            typescheck[attr].append(attrdict['type'])
        # Check that the type of a given attribute is consistent among
        # footprints (warning only)
        for attr, typelist in typescheck.items():
            if len(typelist) > 1:
                fine = True
                for i in range(len(typelist) - 1, 0, -1):
                    fine = fine and issubclass(typelist[i], typelist[i - 1])
                if not fine:
                    logger.warning('%s: Type inconsistency among footprints for attribute %s: %s',
                                   myclsname, attr, ",".join([repr(x) for x in typelist]))
        util.dictmerge(fp, util.list2dict(kw, ('attr', 'only')))
        for a in fp['attr'].keys():
            fp['attr'][a].setdefault('default', None)
            fp['attr'][a].setdefault('optional', False)
            fp['attr'][a].setdefault('access', 'rxx')
            fp['attr'][a].setdefault('doc_visibility', doc.visibility.DEFAULT)  # @UndefinedVariable
            fp['attr'][a].setdefault('doc_zorder', 0)
            # doc_zorder is beetween -100 and 100
            fp['attr'][a]['doc_zorder'] = min(max(-100, fp['attr'][a]['doc_zorder']), 100)
            fp['attr'][a]['alias'] = set(fp['attr'][a].get('alias', set()))
            fp['attr'][a]['remap'] = dict(fp['attr'][a].get('remap', dict()))
            autoremap = fp['attr'][a]['remap'].pop('autoremap', None)
            if autoremap is not None:
                autoremap = util.mktuple(autoremap)
                if 'first' in autoremap:
                    vfirst = fp['attr'][a]['values'][0]
                    for x in fp['attr'][a]['values'][1:]:
                        fp['attr'][a]['remap'][x] = vfirst
            fp['attr'][a]['values'] = set(fp['attr'][a].get('values', set()))
            fp['attr'][a]['outcast'] = set(fp['attr'][a].get('outcast', set()))
            ktype = fp['attr'][a].get('type', str)
            kargs = fp['attr'][a].get('args', dict())
            for autoreclass in ('values', 'outcast'):
                for v in fp['attr'][a][autoreclass]:
                    if not isinstance(v, ktype):
                        fp['attr'][a][autoreclass].remove(v)
                        try:
                            v = ktype(v, **kargs)
                            fp['attr'][a][autoreclass].add(v)
                            logger.debug('Init Footprint [%s] %s reclassed = %s', autoreclass, a, v)
                        except Exception:
                            logger.error('Bad init footprint in [%s]', autoreclass)
                            raise
        self._fp = fp
        self._firstguess_keys_internal = None
        self._resolve_keys_internal = None

        # Instance docstring...
        if setup.docstrings:
            self.__doc__ = doc.format_docstring(self, setup.docstrings, abstractfpobj=True)

    @property
    def _fastkeys(self):
        return self._fp.get('fastkeys', set())

    @property
    def _resolve_keys(self):
        if self._resolve_keys_internal is None:
            candidates = list()
            for k, item in self.attr.items():
                candidates.append((not item['optional'], k in self._fastkeys or k in setup.fastkeys, k))
            candidates.sort(reverse=True)
            self._resolve_keys_internal = [list(), list(), None]
            for item in candidates:
                self._resolve_keys_internal[0].append(item[2])  # key name
                self._resolve_keys_internal[1].append(item[1])  # fast
            self._resolve_keys_internal[0] = collections.deque(self._resolve_keys_internal[0])
            self._resolve_keys_internal[1] = collections.deque(self._resolve_keys_internal[1])
            self._resolve_keys_internal[2] = set(self._resolve_keys_internal[0])
        return [collections.deque(self._resolve_keys_internal[0]),
                collections.deque(self._resolve_keys_internal[1]),
                set(self._resolve_keys_internal[2])]

    @property
    def _firstguess_keys(self):
        if self._firstguess_keys_internal is None:
            self._firstguess_keys_internal = collections.deque()
            for k, item in self.attr.items():
                kdefault = item['default']
                self._firstguess_keys_internal.append(
                    (k, item['optional'], item['alias'], kdefault, hasattr(kdefault, 'footprint_value'))
                )
        return self._firstguess_keys_internal

    def __str__(self):
        return str(self.attr)

    def __repr__(self):
        """A condensed string representation of the present Footprint."""
        return ('<{:s} object at {!s} | info="{:s}">'
                .format(self.__class__.__name__, hex(id(self)), self.info))

    def allkeys(self):
        """Return a set of possible keys for the footprint's attributes."""
        allk = set()
        atfp = self.attr
        for a in atfp:
            allk.add(a)
            allk |= atfp[a]['alias']
        return allk

    def as_dict(self):
        """
        Returns a shallow copy of the internal footprint structure as a pure dictionary.
        """
        return dict(self._fp)

    def as_copy(self):
        """
        Returns a deep copy of the internal footprint structure as a pure dictionary.
        Be aware that some objects such as compiled regular expressions remain identical
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
        """Returns a nice dump version of the actual footprint."""
        return dump.get().cleandump(self._fp)

    def track(self, desc):
        """Returns if the items of ``desc`` are found in the specified footstep ``fp``."""
        fpa = self._fp['attr']
        attrs = list(fpa.keys())
        aliases = []
        for x in attrs:
            aliases.extend(fpa[x]['alias'])
        return [a for a in desc if a in attrs or a in aliases]

    def optional(self, a):
        """Returns whether the given attribute ``a`` is optional or not in the current footprint."""
        return self._fp['attr'][a]['optional']

    def mandatory(self):
        """Returns the list of mandatory attributes in the current footprint."""
        fpa = self._fp['attr']
        return [x for x in fpa.keys() if not fpa[x]['optional']]

    def _firstguess(self, desc, resolvecache=None):
        """Produces a complete guess of the actual footprint according to actual description ``desc``."""
        if resolvecache is None:
            resolvecache = collectors.ResolveCache()
        guess = dict()
        param = resolvecache.defaults
        inputattr = set()
        for k, kopt, kalias, kdefault, kxdefault in self._firstguess_keys:
            if k in desc and not (kopt and desc[k] is None):
                guess[k] = desc[k]
                inputattr.add(k)
                # logger.debug(' > Attr %s in description : %s', k, desc[k])
            else:
                alias_ok = False
                for a in kalias:
                    if a in desc and not (kopt and desc[a] is None):
                        guess[k] = desc[a]
                        inputattr.add(k)
                        alias_ok = True
                        break

                if not alias_ok:
                    if k in param:
                        guess[k] = param[k]
                        inputattr.add(k)
                    else:
                        if kopt:
                            if kdefault is None:
                                guess[k] = UNKNOWN
                            else:
                                if kxdefault:
                                    guess[k] = kdefault.footprint_value()
                                else:
                                    guess[k] = kdefault
                        else:
                            guess[k] = None

        return (guess, inputattr)

    def _findextras(self, desc, resolvecache=None):
        """
        Return a flat dictionary including ground values as defined by ``setup.extras``
        extended by a dictionary view of any :class:`FootprintBase` object found
        in ``desc`` values.
        """
        if resolvecache is None:
            resolvecache = collectors.ResolveCache()
        extras = dict(resolvecache.extras)
        for vdesc in desc.values():
            if isinstance(vdesc, FootprintBase):
                additems = resolvecache.get_shallow_fp(vdesc)
                extras.update(additems)
        # if extras:
        #    logger.debug(' > Extras : %s', extras)
        return extras

    def _addextras(self, extras, guess, more):
        """
        Extend the specified ``extras`` dictionay with pairs of key/value
        suggested in the ``more`` dictionary which are not already defined
        in ``extras`` or the actual ``guess``.
        """
        for k in more.keys():
            if k not in extras and k not in guess:
                extras[k] = more[k]

    def _process_replm(self, replkv, replm, guessk, changed,
                       guess, extras, myautofmt,
                       requeue=False):
        """
        Deal with calls to properties or methods during the replacement process.
        """
        starter = replkv
        replms = re.split(':+', replm)
        for replm in replms:
            subattr = getattr(starter, replm, None)
            if subattr is None:
                guessk = None
                break
            else:
                if callable(subattr):
                    if isinstance(subattr, types.BuiltinFunctionType):
                        starter = subattr()
                    else:
                        try:
                            starter = subattr(guess, extras)
                        except Exception as trouble:
                            logger.critical(trouble)
                            if requeue:
                                starter = '__SKIP__'
                                changed = 0
                                break
                            else:
                                raise
                    if starter is None:
                        guessk = None
                        break
                else:
                    starter = subattr
        if guessk is not None and starter != '__SKIP__':
            guessk = replattr.sub(myautofmt(starter), guessk, 1)
        return guessk, changed

    def _replacement(self, nbpass, k, kfast, guess, extras,
                     todok, todokfast, todokset):
        """
        Try to resolve any replacement sequence inside the ``guess[k]`` value
        according to actual values in the ``guess`` or ``extras`` current dictionaries.

        A replacement sequence is a list of one or more items in brackets of the form:

          * '[key-name]'
          * '[key-name:attr-name]' or '[key-name::attr-name]'
          * '[key-name:meth-name]' or '[key-name::meth-name]'

        If the ``key-name`` could not be found in the actual ``guess`` or ``extras`` dictionaries
        the method raises an :exception:`FootprintUnreachableAttr`.

        Additional flags can be added:

          * '[key-name#01]'  will result in '01' if key-name is not in ``guess`` nor in ``extras``
            (instead of raising a :exception:`FootprintUnreachableAttr` exception.)
          * '[key-name%03d]' will print the value of key-name using the '03d' format string.
            If the format string is incorrect, or if it can not be applied to key-name, a
            :exception:`ValueError` exception will be raised
        """
        if nbpass > 50:
            logger.error('Resolve probably cycling too much... %d tries ?', nbpass)
            raise FootprintMaxIter('Too many Footprint replacements')

        guessk = guess[k]

        changed = 1
        while changed:
            changed = 0
            if isinstance(guessk, str):
                mobj = replattr.search(guessk)
                if mobj:
                    replk = mobj.group(1)
                    replm = mobj.group(2)
                    replx = mobj.group(3)

                    def myautofmt(repl, myfmt=mobj.group(4)):
                        if myfmt:
                            f_formatter = util.FoxyFormatter()
                            thefmt = ("{0" + myfmt + "}" if (':' in myfmt or '!' in myfmt)
                                      else "{0:" + myfmt + "}")
                            try:
                                return f_formatter.format(thefmt, repl)
                            except (ValueError, AttributeError):
                                logger.error('Formating failed for %s. Please check the format string.',
                                             mobj.group(0))
                                raise
                        else:
                            return str(repl)

                    if replk not in guess and replk not in extras:
                        if replx:
                            changed = 1
                            # Here we do not call _autofmt since replx is already a str
                            guessk = replattr.sub(replx, guessk, 1)
                        else:
                            logger.error('No %s attribute in guess:', replk)
                            logger.error('%s', guess)
                            logger.error('No %s attribute in extras:', replk)
                            logger.error('%s', extras)
                            logger.error('Actual defaults: %s', setup.defaults)
                            raise FootprintUnreachableAttr('Could not replace attribute ' + replk)
                    if replk in guess:
                        if replk not in todok:
                            changed = 1
                            if replm:
                                replk_v = guess[replk]
                                guessk, changed = self._process_replm(replk_v, replm, guessk, changed,
                                                                      guess, extras, myautofmt, requeue=False)
                            else:
                                guessk = replattr.sub(myautofmt(guess[replk]), guessk, 1)
                    elif replk in extras:
                        changed = 1
                        if replm:
                            replk_v = extras[replk]
                            guessk, changed = self._process_replm(replk_v, replm, guessk, changed,
                                                                  guess, extras, myautofmt, requeue=True)
                        else:
                            guessk = replattr.sub(myautofmt(extras[replk]), guessk, 1)

        if (guessk is not None and
                isinstance(guessk, str) and
                replattr.search(guessk)):
            # logger.debug(' > Requeue resolve < %s > : %s (npass=%d)', k, guessk, nbpass)
            todok.append(k)
            todokfast.append(kfast)
            todokset.add(k)
            return False
        else:
            # logger.debug(' > No more substitution for %s (npass=%d)', k, nbpass)
            guess[k] = guessk
            return True

    def in_values(self, item, values):
        """Check that item is inside ``values`` or compares as equal to one of these values."""
        if item in values:
            return True
        else:
            return bool([x for x in values if x == item])

    def resolve(self, desc, **kw):
        """Try to guess how the given description ``desc`` could possibly match the current footprint."""
        opts = dict(fatal=setup.fatal, fast=setup.fastmode)
        opts.update(kw)
        opts_fatal = opts['fatal']  # Shortcut for faster execution
        opts_fast = opts['fast']  # Shortcut for faster execution
        report = opts.pop('report', False) or setup.nullreport
        resolvecache = opts.pop('resolvecache', None)
        if resolvecache is None:
            resolvecache = collectors.ResolveCache()

        guess, attr_input = self._firstguess(desc, resolvecache=resolvecache)
        extras = self._findextras(desc, resolvecache=resolvecache)
        attr_seen = set()

        # Add arguments from current description not yet used to extra parameters
        self._addextras(extras, guess, desc)

        if setup.extended:
            # + Add arguments from defaults footprint not already defined to extra parameters
            self._addextras(extras, guess, setup.defaults)

        attrs = self.attr

        if None in guess.values():
            todok = []
            todokfast = []
            todokset = set()
        else:
            todok, todokfast, todokset = self._resolve_keys

        nbpass = 0
        diags = dict()

        while todok:

            k = todok.popleft()
            kfast = todokfast.popleft()
            todokset.discard(k)
            kdef = attrs[k]
            nbpass += 1
            if (not self._replacement(nbpass, k, kfast, guess, extras, todok, todokfast, todokset) or
                    guess[k] is None):
                continue

            attr_seen.add(k)

            while guess[k].__hash__ is not None and guess[k] in kdef['remap']:
                # logger.debug(' > Attr %s remap(%s) = %s', k, guess[k], kdef['remap'][guess[k]])
                guess[k] = kdef['remap'][guess[k]]

            if guess[k] is not UNKNOWN:
                ktype = kdef.get('type', str)
                if kdef.get('isclass', False):
                    if not issubclass(guess[k], ktype):
                        # logger.debug(' > Attr %s class %s not a subclass %s', k, guess[k], ktype)
                        report.add(attribute=k, why=reporting.REPORT_WHY_SUBCLASS, args=ktype.__name__)
                        diags[k] = True
                        guess[k] = None
                elif not isinstance(guess[k], ktype):
                    # logger.debug(' > Attr %s reclass(%s) as %s', k, guess[k], ktype)
                    kwargs = kdef.get('args', dict())
                    try:
                        guess[k] = ktype(guess[k], **kwargs)
                        # logger.debug(' > Attr %s reclassed = %s', k, guess[k])
                    except (ValueError, TypeError, FootprintException):
                        # logger.debug(' > Attr %s badly reclassed as %s = %s', k, ktype, guess[k])
                        report.add(attribute=k, why=reporting.REPORT_WHY_RECLASS,
                                   args=(ktype.__name__, str(guess[k])))
                        diags[k] = True
                        guess[k] = None
                if kdef['values'] and not self.in_values(guess[k], kdef['values']):
                    # logger.debug(' > Attr %s value not in range = %s %s', k, guess[k], kdef['values'])
                    report.add(attribute=k, why=reporting.REPORT_WHY_OUTSIDE, args=guess[k])
                    diags[k] = True
                    guess[k] = None
                if kdef['outcast'] and self.in_values(guess[k], kdef['outcast']):
                    # logger.debug(' > Attr %s value excluded from range = %s %s', k, guess[k], kdef['outcast'])
                    report.add(attribute=k, why=reporting.REPORT_WHY_OUTCAST, args=guess[k])
                    diags[k] = True
                    guess[k] = None

            if (opts_fast or kfast) and guess[k] is None:
                # logger.debug(' > Fast exit from resolve on key "%s" (fast=%s, fastkey=%s)',
                #              k, str(opts_fast), str(kfast))
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
                if opts_fatal:
                    logger.info('No valid attribute "%s" is fatal', k)
                    raise FootprintFatalError('No attribute `' + k + '` is fatal')
                # else:
                #     logger.debug(' > No valid attribute %s', k)
            else:
                if 'weak' in attrs[k]['access']:
                    guess[k] = weakref.proxy(guess[k])

        return (guess, attr_input, attr_seen)

    def checkonly(self, rd, report=setup.nullreport, resolvecache=None):
        """Ensure that the resolved description also matches at least one item per ``only`` feature."""
        if resolvecache is None:
            resolvecache = collectors.ResolveCache()
        params = resolvecache.defaults
        for k, v in self.only.items():
            if not hasattr(v, '__iter__'):
                v = (v,)

            actualattr = k
            after, before = False, False
            if k.startswith('after_'):
                after = True
            if k.startswith('before_'):
                before = True
            if after or before:
                actualattr = k.partition('_')[-1]

            actualvalue = rd.get(actualattr, params.get(actualattr, None))
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
                    checkflag = checkflag or actualvalue == checkvalue

            if not checkflag:
                rd = False
                if report:
                    report.add(attribute=actualattr, only=reporting.REPORT_ONLY_NOTMATCH, args=v)
                break

        return rd

    def get_values(self, attrname):
        """Return acceptable values for a given ``attrname``."""
        return tuple(self.attr[attrname]['values'])

    def get_outcast(self, attrname):
        """Return inacceptable values for a given ``attrname``."""
        return tuple(self.attr[attrname]['outcast'])

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
        """Read-only property. Direct access to internal footprint restriction rules."""
        return self._fp['only']

    @property
    def priority(self):
        """Read-only property. Direct access to internal footprint priority rules."""
        return self._fp['priority']

    @property
    def level(self):
        """Read-only property. Direct access to internal footprint priority level."""
        return self.priority['level']


class DecorativeFootprint(Footprint):
    """
    This class extends the :class:`Footprint` class. In addition to the definition
    and processing of the footprint itself, a class decorator can be registered.

    The :class:`FootprintBaseMeta` will apply this decorator on the target class
    only when the footprint is used directly (i.e. not when inherited).
    """

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._decorators = list()
        for a in args:
            if isinstance(a, DecorativeFootprint):
                self._decorators.extend(a.decorators)
        if 'decorator' in kw:
            self._decorators.extend(kw['decorator'] if isinstance(kw['decorator'], list)
                                    else [kw['decorator'], ])
            if not all([callable(d) for d in self._decorators]):
                raise ValueError("Class decorators must be callables")

    @property
    def decorators(self):
        return self._decorators

    def as_footprint(self):
        return Footprint(self._fp)


class FootprintBaseMeta(type):
    """
    Meta class constructor for :class:`FootprintBase`.
    The current :data:`_footprint` data which could be a simple dict
    or a :class:`Footprint` object is used to instantiate a new :class:`Footprint`,
    built as a merge of the footprint of the base classes.
    """

    def __new__(cls, n, b, d):
        """
        This meta-constructor is in charge of the footprints merging,
        class registering in footprint collectors and documentation setting.
        """
        logger.debug('Base class for footprint usage "%s / %s", bc = (%s), internal = %s', cls, n, b, d)
        abstract = d.setdefault('_abstract', False)
        mkshort = d.setdefault('_mkshort', setup.shortnames)

        # Footprint merging
        fplocal = d.get('_footprint', dict())
        localdeco = list()
        bcfp = [c.__dict__.get('_footprint', dict()) for c in b]
        bcfp.reverse()  # That way, footprint's inheritance is consistent with python's
        if type(fplocal) is list:
            bcfp.extend(fplocal)
            for fptmp in fplocal:
                if isinstance(fptmp, DecorativeFootprint):
                    localdeco.extend(fptmp.decorators)
        else:
            bcfp.append(fplocal)
            if isinstance(fplocal, DecorativeFootprint):
                localdeco.extend(fplocal.decorators)
        thisfp = d['_footprint'] = Footprint(*bcfp, myclsname=n)

        # Setting descriptors for footprint attributes
        d['_fp_auth'] = hash(d['__module__'] + '.' + n)
        active_accessors = access.attr_descriptors()
        for k in thisfp.attr.keys():
            k_info = thisfp.attr[k].get('info', None)
            if setup.docstrings > 1:
                k_info = (k_info or '').rstrip('.') + ' (see the documentation above for more details).'
            if isinstance(thisfp.attr[k]['access'], access.FootprintAttrDescriptor):
                d[k] = thisfp.attr[k]['access'](k, auth=d['_fp_auth'], doc=k_info)
            else:
                try:
                    d[k] = active_accessors[thisfp.attr[k]['access']](
                        k, auth=d['_fp_auth'], doc=k_info
                    )
                except AttributeError:
                    logger.error('Could not find any local descriptor with acces mode %s',
                                 thisfp.attr['access'])
                    raise

        # Possibly use short method names
        if mkshort:
            for k in [x for x in d.keys() if x.startswith('footprint_')]:
                kshort = k.replace('footprint_', '')
                if kshort in d:
                    logger.warning('Shortcut to already defined attribute [%s]', k)
                else:
                    d[kshort] = d.get(k)

        # At least build the class itself as a default type
        realcls = super().__new__(cls, n, b, d)

        # Apply local decorators
        for deco in localdeco:
            realcls = deco(realcls)

        # A class that is not abstrat should register in dedicated collectors
        if not abstract:
            if realcls._explicit and not realcls.footprint_mandatory():
                raise FootprintInvalidDefinition('Explicit class without any mandatory footprint attribute.')
        # Add all classes in collectors but take into accout the abstract key
        for cname in realcls._collector:
            if cname in thisfp.allkeys():
                raise FootprintInvalidDefinition('A attribute or alias name is equal to collector tag: ' +
                                                 cname)
            thiscollector = collectors.get(tag=cname, report=setup.report, lreport_len=setup.lreport_len,
                                           report_style=setup.report_style)
            thiscollector.add(realcls, abstract=abstract)
            if not abstract and thiscollector.register:
                observer.get(tag=realcls.fullname()).register(thiscollector)
                logger.debug('Register class %s in collector %s (%s)', realcls, thiscollector, cname)

        # Docstring building
        basedoc = realcls.__doc__
        if not basedoc:
            basedoc = 'Not documented yet.'
        realcls.__doc__ = basedoc
        if setup.docstrings:
            realcls.__doc__ += doc.format_docstring(realcls._footprint,
                                                    setup.docstrings)

        return realcls


# noinspection PyUnresolvedReferences
class FootprintBase(metaclass=FootprintBaseMeta):
    """
    Base class for any other thematic class that would need to incorporate a :class:`Footprint`.
    Its metaclass is :class:`FootprintBaseMeta`.
    """

    _footprint = Footprint()
    _abstract = True
    _explicit = True
    _reusable = True
    _collector = ('garbage',)

    def __init__(self, *args, **kw):
        logger.debug('Abstract %s init', self.__class__)
        if self.__class__._abstract:
            raise FootprintInvalidDefinition('Could not instanciate abstract class.')
        checked = kw.pop('checked', False)
        self._attributes = dict()
        self._puredict = None
        for a in args:
            logger.debug('FootprintBase %s arg %s', object.__repr__(self), a)
            if isinstance(a, dict):
                self._attributes.update(a)
        self._attributes.update(kw)
        if not checked:
            logger.debug('Resolve attributes at footprint init %s', object.__repr__(self))
            self._attributes, u_attr_input, u_attr_seen = self._footprint.resolve(self._attributes,  # @UnusedVariable
                                                                                  fatal=True)
        self._observer = observer.get(tag=self.__class__.fullname())
        self.footprint_riseup()

    @classmethod
    def footprint_clskind(cls):
        """Return a lower-case string of the name of the current footprint class."""
        return cls.__name__.lower()

    @classmethod
    def footprint_clsrealkind(cls):
        """Return the ``realkind`` property value of the current class."""
        return getattr(cls, 'realkind').fget(cls)

    @property
    def realkind(self):
        """Actual footprint kind, by default the clskind."""
        return 'footprintbase'

    @property
    def footprint(self):
        """Footprint associated to current object's class."""
        return self.__class__._footprint

    def footprint_clsname(self):
        """Returns the short name of the object's class."""
        return self.__class__.__name__

    @classmethod
    def footprint_retrieve(cls, **kw):  # @UnusedVariable
        """Returns the internal checked ``footprint`` of the current class object."""
        return cls._footprint

    @classmethod
    def footprint_reusable(cls):
        """Returns whether the current class could be used for default loading."""
        return cls._reusable

    @classmethod
    def footprint_abstract(cls):
        """Returns whether the current class could be instanciated or not."""
        return cls._abstract

    @classmethod
    def fullname(cls):
        """Returns a nicely formatted name of the current class (dump usage)."""
        return '{:s}.{:s}'.format(cls.__module__, cls.__name__)

    def SUPER(self):
        """A kind of shortcut to parent class. Warning: use with care."""
        return super(self.__class__, self)

    def footprint_riseup(self):
        """Things to do after new or init construction."""
        self._observer.notify_new(self, dict())

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['_observer']
        return d

    def __setstate__(self, state):
        self._observer = observer.get(tag=self.__class__.fullname())
        self.__dict__.update(state)
        self.footprint_riseup()

    def footprint_getattr(self, attr, auth=None):  # @UnusedVariable
        """Return actual attribute value in internal storage. Protected method."""
        thisattr = self._attributes.get(attr, None)
        if thisattr is UNKNOWN:
            thisattr = None
        return thisattr

    def footprint_setattr(self, attr, value, auth=None):
        """Set actual attribute to the value specified. Protected method."""
        if auth != self._fp_auth:
            raise AttributeError("Can't set attribute without valid authorization")
        self._attributes[attr] = value

    def footprint_delattr(self, attr, auth=None):
        """Delete actual attribute. Protected method."""
        if auth != self._fp_auth:
            raise AttributeError("Can't set attribute without valid authorization")
        del self._attributes[attr]

    def footprint_undefs(self):
        """Return list of attributes which are still None."""
        return [a for a in self.footprint_attributes if self.footprint_getattr(a) is None]

    def footprint_clone(self, full=False, extra=None):
        """
        Return a deep copy of the current object as a brand new one.
        Only footprint attributes are carried around.
        Attributes to be replaced or added can be specified in dict **extra**.
        """
        attrs = self._attributes.copy()
        if extra is not None:
            attrs.update(extra)
        objcp = self.__class__(**attrs)
        if full:
            for a in [x for x in self.__dict__.keys() if not x.startswith('_')]:
                setattr(objcp, a, getattr(self, a))
        return objcp

    def footprint_has_attribute(self, attr):
        """Check if the footprint contains the **attr** attribute"""
        return attr in self._attributes

    @property
    def footprint_attributes(self):
        """Returns the list of current attributes."""
        return sorted(self._attributes.keys())

    @property
    def footprint_attributes_values(self):
        """Returns the list of current attributes values."""
        return sorted(self._attributes.values())

    def footprint_as_shallow_dict(self):
        """Returns a dictionary that contains the current attributes (shallow copy)."""
        _puredict = dict()
        for k in self._attributes.keys():
            _puredict[k] = getattr(self, k)
        return _puredict

    def footprint_as_dict(self):
        """Returns a dictionary that contains a deepcopy of the current attributes."""
        puredict = dict()
        for k in self._attributes.keys():
            puredict[k] = copy.deepcopy(getattr(self, k))
        return puredict

    def footprint_export(self):
        """See the current footprint as a pure dictionary when exported."""
        exd = dict()
        for k in self._attributes.keys():
            exportmethod = 'footprint_export_' + k
            if hasattr(self, exportmethod):
                exd[k] = getattr(self, exportmethod)()
            else:
                thisattr = getattr(self, k)
                if hasattr(thisattr, 'footprint_export'):
                    exd[k] = thisattr.footprint_export()
                elif hasattr(thisattr, 'export_dict'):
                    exd[k] = thisattr.export_dict()
                else:
                    exd[k] = copy.deepcopy(thisattr)
        return exd

    def _str_more(self):
        """Additional information to be combined in repr output."""
        return 'footprint={!s}'.format(len(self._attributes))

    def __str__(self):
        """
        Basic layout for nicely formatted print, built as the concatenation
        of the class full name and some :meth:`_str_more` additional information.
        """
        return '{:s} | {:s}>'.format(repr(self).rstrip('>'), self._str_more())

    @property
    def footprint_info(self):
        """Information from the current footprint."""
        return self._footprint.info

    @classmethod
    def footprint_mandatory(cls):
        """
        Returns the attributes that should be present in a description
        in order to be able to match the current object.
        """
        return cls._footprint.mandatory()

    @classmethod
    def footprint_optional(cls, a):
        """Returns whether the specified attribute ``a`` is optional or not."""
        return cls._footprint.optional(a)

    @classmethod
    def footprint_couldbe(cls, rd, report=None, mkreport=False, resolvecache=None):
        """
        This is the heart of any selection purpose, particularly in relation
        with the :meth:`find_all` mechanism of :class:`footprints.Collector` classes.
        It returns the *resolved* form in which the current ``rd`` description
        could be recognized as a footprint of the current class, :data:`False` otherwise.
        """
        if mkreport and not report:
            report = reporting.get(tag='void')
            report.add(collector=proxy.garbages)
        if report:
            report.add(candidate=cls)
        fp = cls._footprint
        resolved, attr_input, u_attr_seen = fp.resolve(rd, fatal=False, report=report,  # @UnusedVariable
                                                       resolvecache=resolvecache)
        if resolved and None not in resolved.values():
            return (fp.checkonly(resolved, report, resolvecache=resolvecache),
                    attr_input)
        else:
            if mkreport:
                report.last.lightdump()
            return (False, attr_input)

    def footprint_compatible(self, rd):
        """
        Resolve a subset of a description according to my footprint,
        and then compare to my actual values.
        """
        fp = self.footprint
        resolved, u_inputattr, u_attr_seen = fp.resolve(rd, fatal=False, report=None)  # @UnusedVariable
        rc = resolved and None not in resolved.values()
        if rc:
            for k in resolved.keys():
                if self._attributes[k] != resolved[k]:
                    rc = False
                    break
        return rc

    def footprint_cleanup(self, rd):
        """
        Removes in the specified ``rd`` description the keys that are
        tracked as part of the footprint of the current object.
        """
        fp = self.footprint
        for attr in fp.track(rd):
            logger.debug('Removing attribute %s : %s', attr, rd[attr])
            del rd[attr]
        return rd

    @classmethod
    def footprint_weight(cls, realinputs):
        """Tuple with ordered weights to make a choice possible between various electible footprints."""
        fp = cls._footprint
        return (fp.priority['level'].rank, realinputs)

    @classmethod
    def footprint_values(cls, attrname):
        """Return the list of authorized values of a footprint attribute (if any)."""
        return list(cls._footprint.attr[attrname]['values'])

    @classmethod
    def footprint_access(cls, attrname):
        """Return the access mode of a footprint attribute."""
        rwd = cls._footprint.attr[attrname]['access']
        if isinstance(rwd, access.FootprintAttrDescriptor):
            rwd = rwd.access_mode
        return rwd

    @classmethod
    def footprint_pl(cls):
        """Return the priority level of the current class footprint object."""
        return cls._footprint.level

    @classmethod
    def footprint_level(cls):
        """Return the tag name of the priority level of the current class footprint object."""
        return cls._footprint.level.tag
