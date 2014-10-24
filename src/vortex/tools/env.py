#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Advanced environment settings.
"""

import os, re, json, traceback

from vortex.autolog import logdefault as logger
from vortex.util.structs import History


#: No automatic export
__all__ = []

#: Pre-compiled evaluation mostly used by :class:`Environment` method (true).
vartrue  = re.compile(r'^\s*(?:[1-9]\d*|ok|on|true|yes|y)\s*$', flags=re.IGNORECASE)

#: Pre-compiled evaluation mostly used by :class:`Environment` method (false).
varfalse = re.compile(r'^\s*(?:0|ko|off|false|no|n)\s*$', flags=re.IGNORECASE)


def paramsmap(_paramsmap=dict()):
    """Cached table of parameters sets currently available."""
    return _paramsmap


def paramstags():
    """List of current tags defined as set of parameters."""
    return paramsmap().keys()


def param(tag='default', pmap=None):
    """
    Returns of defines an dedicated environment to store a set of parameters.
    Different sets could be defined and accessed through specific tagnames.
    """
    if pmap is None:
        pmap = paramsmap()
    if not tag in pmap:
        pmap[tag] = Environment(active=False, clear=True)
    return pmap[tag]


def share(**kw):
    """Populate a special shared environment parameters set."""
    shared = param(tag='shared')
    shared.update(kw)
    return shared


def current():
    """Return current binded :class:`Environment` object."""
    return Environment.current()


class ShellEncoder(json.JSONEncoder):
    """Encoder for :mod:`json` dumps method."""

    def default(self, obj):
        """Overwrite the default encoding if the current object has a ``export_sh`` method."""
        if hasattr(obj, 'export_sh'):
            return obj.export_sh()
        elif hasattr(obj, 'footprint_export'):
            return obj.footprint_export()
        elif hasattr(obj, '__dict__'):
            return vars(obj)
        return json.JSONEncoder.default(self, obj)


class Environment(object):
    """
    Advanced handling of environment features. Either for binding to the system
    or to store and brodacast parameters. Creating an ``active`` environment results
    in the fact that this new environment is binded to the system environment.

    New objects could be instancied from an already existing ``env`` and could be
    active or not according to the flag given at initialisation time.

    The ``clear`` boolean flag implies the cration of an empty environment. In that case
    the new environment is by default not active.

    The ``noexport`` list defines the variables names that would not be broadcasted to the
    system environment.

    An :class:`Environment` could be manipulated as an dictionary for the following mechanisms:

    * key acces / contains
    * len / keys / values
    * iteration
    * callable
    """

    _os = list()

    def __init__(self, env=None, active=False, clear=False, verbose=False, noexport=[]):
        self.__dict__['_history'] = History(tag='env')
        self.__dict__['_active']  = False
        self.__dict__['_verbose'] = verbose
        self.__dict__['_pool']    = dict()
        self.__dict__['_mods']    = set()
        if env is not None and isinstance(env, Environment):
            self._pool.update(env)
        else:
            if clear:
                active = False
            else:
                if self.__class__._os:
                    self._pool.update(self.__class__._os[-1])
                else:
                    self._pool.update(os.environ)
        self.__dict__['_noexport'] = [x.upper() for x in noexport]
        self.active(active)

    @property
    def history(self):
        return self._history

    def __str__(self):
        return '{0:s} | including {1:d} variables>'.format(repr(self).rstrip('>'), len(self))

    def __getstate__(self):
        return self.__dict__

    @classmethod
    def current(cls):
        """Return current binded environment object."""
        return cls._os[-1]

    @classmethod
    def osstack(cls):
        """Return a list of the environment binding stack."""
        return cls._os[:]

    def dumps(self, value):
        """Dump the specified ``value`` as a string."""
        if isinstance(value, str):
            obj = value
        elif hasattr(value, 'export_sh'):
            obj = value.export_sh()
        elif hasattr(value, 'footprint_export'):
            obj = value.footprint_export()
        elif hasattr(value, '__dict__'):
            obj = vars(obj)
        else:
            obj = value
        return str(obj)

    def setvar(self, varname, value):
        """
        Set uppercase ``varname`` to value.
        Also used as internal for attribute access or dictionary access.
        """
        upvar = varname.upper()
        self._pool[upvar] = value
        self._mods.add(upvar)
        self.history.append(upvar, value, traceback.format_stack()[:-1])
        if self.osbound():
            if isinstance(value, str):
                actualvalue = str(value)
            else:
                actualvalue = json.dumps(value, cls=ShellEncoder)
            os.environ[upvar] = actualvalue
            if self.verbose():
                if self.osbound() and self._sh:
                    self._sh.stderr('export', '{0:s}={1:s}'.format(upvar, actualvalue))
                logger.debug('Env export %s="%s"', upvar, actualvalue)

    def __setitem__(self, varname, value):
        return self.setvar(varname, value)

    def __setattr__(self, varname, value):
        return self.setvar(varname, value)

    def getvar(self, varname):
        """
        Get ``varname`` value (this is not case sensitive).
        Also used as internal for attribute access or dictionary access.
        """
        if varname in self._pool:
            return self._pool[varname]
        elif varname.upper() in self._pool:
            return self._pool[varname.upper()]
        else:
            return None

    def __getitem__(self, varname):
        return self.getvar(varname)

    def __getattr__(self, varname):
        if varname.startswith('_'):
            raise AttributeError
        else:
            return self.getvar(varname)

    def delvar(self, varname):
        """
        Delete ``varname`` from current environment (this is not case sensitive).
        Also used as internal for attribute access or dictionary access.
        """
        seen = 0
        if varname in self._pool:
            seen = 1
            del self._pool[varname]
        if varname.upper() in self._pool:
            seen = 1
            del self._pool[varname.upper()]
        if seen and self.osbound():
            del os.environ[varname.upper()]
            if self.verbose() and self._sh:
                self._sh.stderr('unset', '{0:s}'.format(varname.upper()))

    def __delitem__(self, varname):
        self.delvar(varname)

    def __delattr__(self, varname):
        self.delvar(varname)

    def __len__(self):
        return len(self._pool)

    def __iter__(self):
        for t in self._pool.keys():
            yield t

    def __contains__(self, item):
        return self.has_key(item)

    def has_key(self, item):
        """
        Returns whether ``varname`` value is defined or not.
        Also used as internal for dictionary access.
        """
        return item in self._pool or item.upper() in self._pool

    def __cmp__(self, other):
        return cmp(self._pool, other._pool)

    def keys(self):
        """Returns the keys of the internal pool of variables."""
        return self._pool.keys()

    def __call__(self):
        return self.pool()

    def values(self):
        """Returns the values of the internal pool of variables."""
        return self._pool.values()

    def pool(self):
        """Returns the reference of the internal pool of variables."""
        return self._pool

    def get(self, *args):
        """Simulates the dictionary ``get`` mechanism on the internal pool of variables."""
        return self._pool.get(args[0].upper(), *args[1:])

    def items(self):
        """Simulates the dictionary ``items`` method on the internal pool of variables."""
        return self._pool.items()

    def iteritems(self):
        return self._pool.iteritems()

    def update(self, *args, **kw):
        """Set a collection of variables given as a list of iterable items or key-values pairs."""
        argd = list(args)
        argd.append(kw)
        for dico in argd:
            for var, value in dico.iteritems():
                self.setvar(var, value)

    def merge(self, mergenv):
        """Incorporates key-values from ``mergenv`` into current environment."""
        self.update(mergenv.pool())

    def clear(self):
        """Flush the current pool of variables."""
        return self._pool.clear()

    def clone(self):
        """Return a non-active copy of the current env."""
        eclone = self.__class__(env=self, active=False)
        try:
            eclone.verbose(self._verbose, self._sh)
        except AttributeError:
            logger.warning('Could not find verbose attributes while cloning env...')
        return eclone

    def native(self, varname):
        """Returns the native form this variable could have in a shell environment."""
        value = self._pool[varname]
        if isinstance(value, str):
            return str(value)
        else:
            return json.dumps(value, cls=ShellEncoder)

    def verbose(self, switch=None, sh=None):
        """Switch on or off the verbose mode. Returns actual value."""
        if switch is not None:
            self.__dict__['_verbose'] = bool(switch)
        if sh is not None:
            self.__dict__['_sh'] = sh
        return self.__dict__['_verbose']

    def active(self, *args):
        """
        Bind or unbind current environment to the shell environment according to a boolean flag
        given as first argument. Returns current active status after update.
        """
        previous = self._active
        osrewind = None
        if args and type(args[0]) is bool:
            self.__dict__['_active'] = args[0]
        if previous and not self._active and self.__class__._os and id(self) == id(self.__class__._os[-1]):
            self.__class__._os.pop()
            osrewind = self.__class__._os[-1]
        if not previous and self._active:
            osrewind = self
            self.__class__._os.append(self)
        if osrewind:
            osrewind.__dict__['_active'] = True
            os.environ.clear()
            for k in filter(lambda x: x not in osrewind._noexport, osrewind._pool.keys()):
                os.environ[k] = osrewind.native(k)
        return self._active

    def nacked(self):
        """Return ``True`` when the pool of variables is empty."""
        return not bool(self._pool)

    def modified(self):
        """Return ``True`` when some variables have been modified."""
        return bool(self._mods)

    def varupdates(self):
        """Return the list of variables names that have been modified so far."""
        return self._mods

    def osbound(self):
        """Returns whether this current environment is bound to the os.environ."""
        return self._active and self.__class__._os and self is self.__class__._os[-1]

    def tracebacks(self):
        """Dump the stack of manipulations of the current environment."""
        for count, stamp, action in self.history:
            varname, value, stack = action
            print "[", stamp, "]", varname, "=", value, "\n"
            for xs in stack:
                print xs

    def osdump(self):
        """Dump the actual values of the OS environment."""
        for k in sorted(os.environ.keys()):
            print '{0:s}="{1:s}"'.format(k, os.environ[k])

    def mydump(self):
        """Dump the actual values of the current environment."""
        for k in sorted(self._pool.keys()):
            print '{0:s}="{1:s}"'.format(k, str(self._pool[k]))

    def trueshell(self):
        return re.sub('^.*/', '', self.getvar('shell'))

    def true(self, varname):
        """Extended boolean positive test of the variable given as argument."""
        return bool(vartrue.match(str(self.getvar(varname))))

    def false(self, varname):
        """Extended boolean negative test of the variable given as argument."""
        xvar = self.getvar(varname)
        if xvar is None:
            return True
        else:
            return bool(varfalse.match(str(xvar)))

    def setbinpath(self, value, pos=None):
        """Insert a new path value to the bin search path at given position."""
        mypath = self.getvar('PATH').split(':')
        value = str(value)
        while value in mypath:
            mypath.remove(value)
        if pos is None:
            pos = len(mypath)
        mypath.insert(pos, value)
        self.setvar('PATH', ':'.join(mypath))

    def rmbinpath(self, value):
        """Remove the specified value from bin path."""
        mypath = self.getvar('PATH').split(':')
        while value in mypath:
            mypath.remove(value)
        self.setvar('PATH', ':'.join(mypath))
