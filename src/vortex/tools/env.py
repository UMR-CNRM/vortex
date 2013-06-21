#!/bin/env python
# -*- coding: utf-8 -*-

r"""
Advanced environment settings.
"""

import os, re, json, traceback
from datetime import datetime

#: No automatic export
__all__ = []

#: Precompiled evaluation mostly used by :class:`Environment` method (true).
vartrue  = re.compile(r'^\s*(?:[1-9]\d*|ok|on|true|yes|y)\s*$', flags=re.IGNORECASE)

#: Precompiled evaluation mostly used by :class:`Environment` method (false).
varfalse = re.compile(r'^\s*(?:0|ko|off|false|no|n)\s*$', flags=re.IGNORECASE)


def param(tag='default', _params=dict()):
    """
    Returns of defines an dedicated environment to store a set of parameters.
    Different sets could be defined and accessed through specific tagnames.
    """
    if not tag in _params:
        _params[tag] = Environment(active=False, clear=True)
    return _params[tag]

def current():
    """Return current binded :class:`Environment` object."""
    return Environment.current()

class ShellEncoder(json.JSONEncoder):
    """Encoder for :mod:`json` dumps method."""

    def default(self, obj):
        """Overwrite the default encoding if the current object has a ``puredict`` method."""
        if hasattr(obj, 'shellexport'):
            return obj.shellexport()
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
        self.__dict__['_history'] = []
        self.__dict__['_active'] = False
        self.__dict__['_verbose'] = False
        self.__dict__['_pool'] = dict()
        self.__dict__['_mods'] = set()
        if env and isinstance(env, Environment):
            self._pool.update(env)
        else:
            if clear:
                active=False
            else:
                if self.__class__._os:
                    self._pool.update(self.__class__._os[-1])
                else:
                    self._pool.update(os.environ)
        self.__dict__['_noexport'] = [x.upper() for x in noexport]
        self.active(active)

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
        elif hasattr(value, 'shellexport'):
            obj = value.shellexport()
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
        self._history.append((upvar, value, datetime.now(), traceback.format_stack()))
        if self.osbound():
            if isinstance(value, str):
                actualvalue = str(value)
            else:
                actualvalue = json.dumps(value, cls=ShellEncoder)
            os.environ[upvar] = actualvalue
            if self.verbose():
                logger.info('Export %s="%s"', upvar, actualvalue)

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
        if seen and self.osbound(): del os.environ[varname.upper()]

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
        Returns either ``varname`` value is defined or not.
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
        return self._pool.get(*args)

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

    def native(self, varname):
        """Returns the native form this variable could have in a shell environment."""
        value = self._pool[varname]
        if isinstance(value, str):
            return str(value)
        else:
            return json.dumps(value, cls=ShellEncoder)

    def verbose(self, switch=None):
        """Switch on or off the verbose mode. Returns actual value."""
        if switch != None:
            self.__dict__['_verbose'] = switch
        return self.__dict__['_verbose']

    def active(self, *args):
        """
        Bind or unbind current environment to the shell environment according to a boolean flag
        given as first argument. Returns current active status after update.
        """
        previous = self._active
        osrewind = None
        if args and type(args[0]) == bool:
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
        """Returns either this current environment is bound to the os.environ."""
        return self._active and self.__class__._os and id(self) == id(self.__class__._os[-1])

    def history(self):
        """Dump the stack of manipulations of the current environment."""
        for action in self._history:
            varname, value, stamp, stack = action 
            print "[", stamp, "]", varname, "=", value, "\n"
            for xs in stack:
                print xs

    def osdump(self):
        """Dump the actual values of the OS environment."""
        for k in sorted(os.environ.keys()):
            print '{0:s}="{1:s}"'.format(k, os.environ[k])  

    def mydump(self):
        """Dump the actual values of the current environment."""
        return [ '{0:s}="{1:s}"'.format(k, self._pool[k]) for k in sorted(self._pool.keys()) ]

    def trueshell(self):
        return re.sub('^.*/', '', self.getvar('shell'))

    def true(self, varname):
        """Extended boolean positive test of the variable given as argument."""
        return bool(vartrue.match(str(self.getvar(varname))))

    def false(self, varname):
        """Extended boolean negative test of the variable given as argument."""
        xvar = self.getvar(varname)
        if xvar == None:
            return True
        else:
            return bool(varfalse.match(str(xvar)))

    def setbinpath(self, value, pos=None):
        """Insert a new path value to the bin search path at given position."""
        mypath = self.getvar('PATH').split(':')
        if pos == None:
            pos = len(mypath)
        mypath.insert(pos, value)
        self.setvar('PATH', ':'.join(mypath))

    def rmbinpath(self, value):
        """Remove the specified value from bin path."""
        mypath = self.getvar('PATH').split(':')
        while value in mypath:
            mypath.remove(value)
        self.setvar('PATH', ':'.join(mypath))
