#!/bin/env python
# -*- coding: utf-8 -*-

"""
Fabric for objects with parametrable footprints, i.e. the set of keys/values
that attributes (possibly optionals) could cover.
"""

#: No automatic export
__all__ = []

import copy, re

import logging
logger = logging.getLogger('footprints')

import priorities, dump, util

UNKNOWN = '__unknown__'
replattr = re.compile(r'\[(\w+)(?:\:+(\w+))?\]')


class MaxLoopIter(Exception):
    pass

class UnreachableAttr(Exception):
    pass

class FootprintSetup(object):
    """Defines some defaults and external tools."""

    def __init__(self, docstring=True, fastmode=False, extended=False, dumper=dump.Dumper(), observers=None, tracker=None):
        self.dumper = dumper
        self.observers = observers
        self.tracker = tracker
        self.extended = extended
        self.docstring = docstring
        self.fastmode = fastmode
        self.ground = dict()
        self.defaults = dict()
        self.defcallback = None

    def setfpenv(self, **kw):
        """Extend the current defaults environnement for footprint resolution."""
        self.defaults.update({ k.lower():v for k,v in kw.items() })
        return self.defaults

    def dumpfpenv(self):
        """Dump the actual values of the default environment."""
        return [ '{0:s}="{1:s}"'.format(k, str(self.defaults[k])) for k in sorted(self.defaults.keys()) ]

    def setfpext(self, switch=None):
        """Commut to extended mode or not for footprint defaults. Return current status."""
        if switch != None:
            self.extended = bool(switch)
        return self.extended

    def extras(self):
        if self.defcallback:
            cb = self.defcallback
            return cb()
        else:
            return dict()

setup = FootprintSetup()

class Footprint(object):

    def __init__(self, *args, **kw):
        """Initialisation and checking of a given set of footprint."""
        nodef = False
        if 'nodefault' in kw:
            nodef = kw['nodefault']
            del kw['nodefault']
        if nodef:
            fp = dict()
        else:
            fp = dict(
                info = 'Not documented',
                attr = dict(),
                bind = list(),
                only = dict(),
                priority = dict( level = priorities.top.TOOLBOX )
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
            fp['attr'][a].setdefault('alias', tuple())
            fp['attr'][a].setdefault('remap', dict())
            fp['attr'][a].setdefault('default', None)
            fp['attr'][a].setdefault('optional', False)
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

    def asopts(self):
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
        return filter(lambda x: not fpa[x]['optional'] or not fpa[x]['default'], fpa.keys())

    def _firstguess(self, desc):
        attrs = self.attr
        guess = dict()
        param = setup.defaults
        inputattr = set()
        for k, kdef in attrs.iteritems():
            if kdef['optional']:
                if kdef['default'] == None:
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
        extras = setup.extras()
        for vdesc in desc.values():
            if isinstance(vdesc, BFootprint): extras.update(vdesc.puredict())
        if extras:
            logger.debug(' > Extras : %s', extras)
        return extras

    def _addextras(self, extras, guess, more):
        for k in [ x.lower() for x in more.keys() ]:
            if k not in extras and k not in guess:
                extras[k] = more[k]

    def _replacement(self, nbpass, k, guess, extras, todo):
        if nbpass > 25:
            logger.error('Resolve probably cycling too much... %d tries ?', nbpass)
            raise MaxLoopIter('Too many Footprint replacements')

        changed = 1
        while changed:
            changed = 0
            mobj = replattr.search(str(guess[k]))
            if mobj:
                replk = mobj.group(1)
                replm = mobj.group(2)
                if replk not in guess and replk not in extras:
                    logger.critical('No %s attribute in guess:', replk)
                    logger.critical('%s', guess)
                    logger.critical('No %s attribute in extras:', replk)
                    logger.critical('%s', extras)
                    raise UnreachableAttr('Could not replace attribute ' + replk)
                if replk in guess:
                    if replk not in todo:
                        changed = 1
                        if replm:
                            subattr = getattr(guess[replk], replm, None)
                            if subattr == None:
                                guess[k] = None
                            else:
                                guess[k] = replattr.sub(str(subattr), guess[k], 1)
                        else:
                            guess[k] = replattr.sub(str(guess[replk]), guess[k], 1)
                elif replk in extras:
                    changed = 1
                    if replm:
                        subattr = getattr(extras[replk], replm, None)
                        if subattr == None:
                            guess[k] = None
                        else:
                            if callable(subattr):
                                try:
                                    attrcall = subattr(guess, extras)
                                except:
                                    attrcall = '__SKIP__'
                                    changed = 0
                                if attrcall == None:
                                    guess[k] = None
                                elif attrcall != '__SKIP__':
                                    guess[k] = replattr.sub(str(attrcall), guess[k], 1)
                            else:
                                guess[k] = replattr.sub(str(subattr), guess[k], 1)
                    else:
                        guess[k] = replattr.sub(str(extras[replk]), guess[k], 1)

        if guess[k] != None and replattr.search(str(guess[k])):
            logger.debug(' > Requeue resolve < %s > : %s', k, guess[k])
            todo.append(k)
            return False
        else:
            logger.debug(' > No more substitution for %s', k)
            return True

    def resolve(self, desc, **kw):
        """Try to guess how the given description ``desc`` could possibly match the current footprint."""

        opts = dict(fatal=True, fast=setup.fastmode, tracker=setup.tracker(tag='fpresolve'))
        if kw: opts.update(kw)

        guess, inputattr = self._firstguess(desc)
        extras = self._findextras(desc)

        # Add arguments from current description not yet used to extra parameters
        self._addextras(extras, guess, desc)

        # Add arguments from defaults footprint not already defined to extra parameters
        if setup.extended:
            self._addextras(extras, guess, setup.defaults)

        attrs = self.attr

        nbpass = 0
        if None in guess.values():
            todo = []
        else:
            todo = attrs.keys()
            try:
                todo.remove('kind')
                todo.insert(0, 'kind')
            except ValueError:
                pass
        replshortcut = self._replacement

        diags = dict()

        while todo:

            k = todo.pop(0)
            kdef = attrs[k]
            nbpass = nbpass + 1
            if not replshortcut(nbpass, k, guess, extras, todo) or guess[k] == None: continue

            while kdef['remap'].has_key(guess[k]):
                logger.debug(' > Attr %s remap(%s) = %s', k, guess[k], kdef['remap'][guess[k]])
                guess[k] = kdef['remap'][guess[k]]

            if guess[k] is UNKNOWN:
                logger.debug(' > Optional attr still unknown : %s', k)
            else:
                ktype = kdef.get('type', str)
                kclass = kdef.get('isclass', False)
                if not isinstance(guess[k], ktype) and not kclass:
                    logger.debug(' > Attr %s reclass(%s) as %s', k, guess[k], ktype)
                    kargs = kdef.get('args', dict())
                    try:
                        guess[k] = ktype(guess[k], **kargs)
                        logger.debug(' > Attr %s reclassed = %s', k, guess[k])
                    except:
                        logger.debug(' > Attr %s badly reclassed as %s = %s', k, ktype, guess[k])
                        opts['tracker'].add('key', k, why='Could not reclass to [{0:s}]: {1:s}'.format(ktype.__name__, str(guess[k])))
                        diags[k] = True
                        guess[k] = None
                if kdef.has_key('values') and guess[k] not in kdef['values']:
                    logger.debug(' > Attr %s value not in range = %s %s', k, guess[k], kdef['values'])
                    opts['tracker'].add('key', k, why='Not in values: {0:s}'.format(str(guess[k])))
                    diags[k] = True
                    guess[k] = None
                if kdef.has_key('outcast') and guess[k] in kdef['outcast']:
                    logger.debug(' > Attr %s value excluded from range = %s %s', k, guess[k], kdef['outcast'])
                    opts['tracker'].add('key', k, why='Outcast value: {0:s}'.format(str(guess[k])))
                    diags[k] = True
                    guess[k] = None

            if guess[k] == None and ( opts['fast'] or k == 'kind' ):
                break

        for k in attrs.keys():
            if guess[k] == 'None':
                guess[k] = None
                logger.warning(' > Attr %s is a null string', k)
                if not k in diags:
                    opts['tracker'].add('key', k, why='Not valid')
            if guess[k] == None:
                inputattr.discard(k)
                if not k in diags:
                    opts['tracker'].add('key', k, why='Missing value')
                if opts['fatal']:
                    logger.critical('No valid attribute %s', k)
                else:
                    logger.debug(' > No valid attribute %s', k)

        return ( guess, inputattr )

    def checkonly(self, rd, tracker):
        """Be sure that the resolved description also match at least one item per ``only`` feature."""

        params = setup.defaults
        for k, v in self.only.items():
            if not hasattr(v, '__iter__'):
                v = (v, )

            after, before = False, False
            if k.startswith('after_'):
                after = True
                k = k.split('after_', 1)[-1]
            if k.startswith('before_'):
                before = True
                k = k.split('before_', 1)[-1]

            actualvalue = rd.get(k, params.get(k.upper(), None))
            if actualvalue == None:
                rd = False
                tracker.add('only', k, why='No value found')
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
                tracker.add('only', k, why='Do not match')
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


class AFootprint(object):
    """Accessor class to footprint attributes."""

    def __init__(self, attr, fget=getattr, fset=setattr, fdel=delattr):
        self.attr = attr
        self.fget = fget
        self.fset = fset
        self.fdel = fdel

    def __get__(self, instance, owner):
        thisattr = instance._attributes.get(self.attr, None)
        if thisattr is UNKNOWN: thisattr = None
        return thisattr

    def __set__(self, instance, value):
        raise AttributeError, 'This attribute should not be overwritten'

    def __delete__(self, instance):
        raise AttributeError, 'This attribute should not be deleted'


class MFootprint(type):
    """
    Meta class constructor for :class:`BFootprint`.
    The current :data:`_footprint` data which could be a simple dict
    or a :class:`Footprint` object is used to instantiate a new :class:`Footprint`,
    built as a merge of the footprint of the base classes.
    """

    def __new__(cls, n, b, d):
        logger.debug('Base class for footprint usage "%s / %s", bc = ( %s ), internal = %s', cls, n, b, d)
        fplocal = d.get('_footprint', dict())
        bcfp = [ c.__dict__.get('_footprint', dict()) for c in b ]
        if type(fplocal) == list:
            bcfp.extend(fplocal)
        else:
            bcfp.append(fplocal)
        d['_footprint'] = Footprint( *bcfp )
        for k in d['_footprint'].attr.keys():
            d[k] = AFootprint(k, fset=None, fdel=None)
        realcls = super(MFootprint, cls).__new__(cls, n, b, d)
        if setup.docstring:
            basedoc = realcls.__doc__
            if not basedoc:
                basedoc = 'Not documented yet.'
            realcls.__doc__ = basedoc + "\n\n    Footprint::\n\n" + realcls.footprint().nice()
        return realcls


class BFootprint(object):
    """
    Base class for any other thematic class that would need to incorporate a :class:`Footprint`.
    Its metaclass is :class:`MFootprint`.
    """

    __metaclass__ = MFootprint

    def __init__(self, *args, **kw):
        logger.debug('Abstract %s init', self.__class__)
        checked = kw.pop('checked', False)
        self._instfp = Footprint(self._footprint.as_dict())
        self._attributes = dict()
        for a in args:
            logger.debug('BFootprint %s arg %s', self, a)
            if isinstance(a, dict):
                self._attributes.update(a)
        self._attributes.update(kw)
        if not checked:
            logger.debug('Resolve attributes at footprint init %s', object.__repr__(self))
            self._attributes, u_inputattr = self._instfp.resolve(self._attributes, fatal=True)
        if setup.observers:
            self._observer = setup.observers.getobserver(self.fullname())
            self._observer.notify_new(self, dict())
        else:
            self._observer = None

    @property
    def realkind(self):
        """Must be implemented by subclasses."""
        pass

    def __del__(self):
        if self._observer:
            self._observer.notify_del(self, dict())

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

    def addrepr(self):
        """Additional information to be combined in repr output."""
        return 'object at ' + hex(id(self))

    def __repr__(self):
        """
        Basic layout for nicely formatted print, built as the concatenation
        of the class full name and some :meth:`addrepr` additional information.
        """
        return '<{0:s} {1:s}>'.format(self.fullname(), self.addrepr())

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
        return cls.footprint().optional()

    @classmethod
    def couldbe(cls, rd, trackroot=None):
        """
        This is the heart of any selection purpose, particularly in relation
        with the :meth:`findall` mechanism of :class:`vortex.utilities.catalogs.ClassesCollector` classes.
        It returns the *resolved* form in which the current ``rd`` description
        could be recognized as a footprint of the current class, :data:`False` otherwise.
        """
        logger.debug('-' * 180)
        logger.debug('Couldbe a %s ?', cls)
        if not trackroot:
            trackroot = setup.tracker('garbage')
        fp = cls.footprint()
        resolved, inputattr = fp.resolve(rd, fatal=False, tracker=trackroot)
        if resolved and None not in resolved.values():
            return ( fp.checkonly(resolved, trackroot), inputattr )
        else:
            return ( False, inputattr )

    def compatible(self, rd):
        """
        Resolve a subset of a description according to my footprint,
        and then compare to my actual values.
        """
        fp = self.footprint()
        resolved, u_inputattr = fp.resolve(rd, fatal=False, fast=False, tracker=None)
        rc = True
        for k in rd.keys():
            if resolved[k] == None or self._attributes[k] != resolved[k]:
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
        try:
            return cls.footprint().attr[attrname]['values']
        except KeyError:
            logger.debug('No values list associated with this attribute %s', attrname)
            return None
