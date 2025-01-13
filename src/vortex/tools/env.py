"""
Advanced environment variables management tools.
"""

import collections
import collections.abc
import json
import os
import re
import traceback

from bronx.fancies import loggers
from bronx.stdtypes.history import PrivateHistory
from vortex.util.structs import ShellEncoder

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

#: Pre-compiled evaluation mostly used by :class:`Environment` method (true).
vartrue = re.compile(
    r"^\s*(?:[1-9]\d*|ok|on|true|yes|y)\s*$", flags=re.IGNORECASE
)

#: Pre-compiled evaluation mostly used by :class:`Environment` method (false).
varfalse = re.compile(r"^\s*(?:0|ko|off|false|no|n)\s*$", flags=re.IGNORECASE)


def current():
    """Return the current active :class:`Environment` object."""
    return Environment.current()


class Environment:
    """
    Advanced handling of environment features. Either for binding to the system
    or to store and broadcast parameters. Activating an environment results
    in the fact that this new environment is binded to the system environment.

    New objects could be instantiated from an already existing ``env`` and could be
    active or not according to the ``active`` flag given at initialisation time.

    An :class:`Environment` could be manipulated as an dictionary for the following
    mechanisms:

    * key access / contains
    * len / keys / values
    * iteration
    * callable

    """

    _current_active = None

    def __init__(
        self,
        env=None,
        active=False,
        clear=False,
        verbose=False,
        noexport=[],
        contextlock=None,
        history=True,
    ):
        """
        :param Environment env: An existing Environment used to initialise this object.
        :param bool active: Is this new environment activated when created.
        :param bool clear: To create an empty environment. (In
            that case the new environment is by default not active).
        :param verbose clear: Activate the verbose mode (every variable exported
            to the system environment will be signalled on stderr).
        :param list[str] noexport: A list of variable names that will never be
            broadcasted to the system environment variables list.
        :param ~vortex.layout.contexts.Context contextlock: The Context
            this environment is associated to. This implies that the
            environment won't activate unless this associated Context is active.
        :param bool history: Record every changes in an
            :class:`~bronx.stdtypes.history.PrivateHistory` object that will be
            accessible through the :attr:`history` property.
        """
        self.__dict__["_history"] = PrivateHistory() if history else None
        self.__dict__["_verbose"] = verbose
        self.__dict__["_frozen"] = collections.deque()
        self.__dict__["_pool"] = dict()
        self.__dict__["_mods"] = set()
        self.__dict__["_sh"] = None
        self.__dict__["_os"] = list()
        if env is not None and isinstance(env, Environment):
            self._env_clone_internals(env, contextlock)
            if verbose:
                try:
                    self.__dict__["_sh"] = env._sh
                except AttributeError:
                    pass
        else:
            if clear:
                active = False
            else:
                if self._current_active is not None:
                    self._env_clone_internals(
                        self._current_active, contextlock
                    )
                else:
                    self._pool.update(os.environ)
        self.__dict__["_noexport"] = [x.upper() for x in noexport]
        self.active(active)

    def _env_clone_internals(self, env, contextlock):
        self.__dict__["_os"] = env.osstack()
        self.__dict__["_os"].append(env)
        self._pool.update(env.items())
        if contextlock is not None:
            self.__dict__["_contextlock"] = contextlock
        else:
            self.__dict__["_contextlock"] = env.contextlock

    @property
    def history(self):
        """
        This environment's :class:`~bronx.stdtypes.history.PrivateHistory`
        object (may be ``None``).
        """
        return self._history

    def _record(self, var, value):
        if self.history is not None:
            self.history.append(var, value, traceback.format_stack()[:-1])

    def __str__(self):
        return "{:s} | including {:d} variables>".format(
            repr(self).rstrip(">"), len(self)
        )

    @classmethod
    def current(cls):
        """Return the current active environment object."""
        return cls._current_active

    def osstack(self):
        """Return a list of the environment binding stack."""
        return self._os[:]

    @property
    def contextlock(self):
        """
        The :class:`~vortex.layout.contexts.Context` this environment is bound
        to (this might return None).
        """
        return self._contextlock

    def dumps(self, value):
        """Dump the specified ``value`` as a string (utility function)."""
        if isinstance(value, str):
            obj = str(value)
        elif hasattr(value, "export_dict"):
            obj = value.export_dict()
        elif hasattr(value, "footprint_export"):
            obj = value.footprint_export()
        elif hasattr(value, "__dict__"):
            obj = vars(value)
        else:
            obj = value
        return str(obj)

    def setvar(self, varname, value, enforce_uppercase=True):
        """Set uppercase ``varname`` to ``value``.

        :param bool enforce_uppercase: All variable names are changed to upper case (default).

        Also used as internal for attribute access or dictionary access.
        """
        upvar = varname.upper() if enforce_uppercase else varname
        upvar = str(upvar)
        self._pool[upvar] = value
        self._mods.add(upvar)
        self._record(upvar, value)
        if self.osbound():
            if isinstance(value, str):
                actualvalue = str(value)
            else:
                actualvalue = json.dumps(value, cls=ShellEncoder)
            os.environ[upvar] = actualvalue
            if self.verbose():
                if self.osbound() and self._sh:
                    self._sh.stderr(
                        "export", "{:s}={:s}".format(upvar, actualvalue)
                    )
                logger.debug('Env export %s="%s"', upvar, actualvalue)

    def __setitem__(self, varname, value):
        return self.setvar(varname, value)

    def __setattr__(self, varname, value):
        return self.setvar(varname, value)

    def getvar(self, varname):
        """Get ``varname`` value (this is not case sensitive).

        Also used as internal for attribute access or dictionary access.
        """
        varname = str(varname)
        if varname in self._pool:
            return self._pool[varname]
        elif varname.upper() in self._pool:
            return self._pool[varname.upper()]
        else:
            return None

    def __getitem__(self, varname):
        return self.getvar(varname)

    def __getattr__(self, varname):
        if varname.startswith("_"):
            raise AttributeError
        else:
            return self.getvar(varname)

    def delvar(self, varname):
        """
        Delete ``varname`` from current environment (this is not case sensitive).

        Also used as internal for attribute access or dictionary access.
        """
        seen = 0
        varname = str(varname)
        if varname in self._pool:
            seen = 1
            del self._pool[varname]
        if varname.upper() in self._pool:
            seen = 1
            del self._pool[varname.upper()]
        if seen and self.osbound():
            del os.environ[varname.upper()]
            if self.verbose() and self._sh:
                self._sh.stderr("unset", "{:s}".format(varname.upper()))
        if seen:
            self._record(varname.upper(), "!!deleted!!")

    def __delitem__(self, varname):
        self.delvar(varname)

    def __delattr__(self, varname):
        self.delvar(varname)

    def __len__(self):
        return len(self._pool)

    def __iter__(self):
        yield from self._pool.keys()

    def __contains__(self, item):
        item = str(item)
        return item in self._pool or item.upper() in self._pool

    def has_key(self, item):
        """Returns whether ``item`` is defined or not.

        Also used as internal for dictionary access.
        """
        return item in self

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
        """Proxy to the dictionary ``get`` mechanism on the internal pool of variables."""
        return self._pool.get(str(args[0]).upper(), *args[1:])

    def items(self):
        """Proxy to the dictionary ``items`` method on the internal pool of variables."""
        return self._pool.items()

    def __eq__(self, other):
        return (
            isinstance(other, type(self))
            and set(self.keys()) == set(other.keys)
            and all([self[k] == other[k] for k in self.keys])
        )

    def __ne__(self, other):
        return not self == other

    def update(self, *args, **kw):
        """Set a collection of variables given as a list of iterable items or key-values pairs."""
        argd = list(args)
        argd.append(kw)
        for dico in argd:
            for var, value in dico.items():
                self.setvar(var, value)

    def delta(self, **kw):
        """
        Temporarily set a collection of variables that could be reversed using
        the :meth:`rewind` method.
        """
        upditems, newitems = (dict(), collections.deque())
        for var, value in kw.items():
            var = str(var)
            if var in self:
                upditems[var] = self.get(var)
            else:
                newitems.append(var)
            self.setvar(var, value)
        self._frozen.append((upditems, newitems))

    def rewind(self):
        """Come back on last environment delta changes (see the :meth:`delta` method)."""
        if self._frozen:
            upditems, newitems = self._frozen.pop()
            while newitems:
                self.delvar(newitems.pop())
            for var, value in upditems.items():
                self.setvar(var, value)
        else:
            raise RuntimeError("No more delta to be rewinded...")

    def delta_context(self, **kw):
        """
        Create a context that will automatically create a delta then rewind it
        when exiting.
        """
        return EnvironmentDeltaContext(self, **kw)

    def default(self, *args, **kw):
        """Set a collection of non defined variables given as a list of iterable items or key-values pairs."""
        argd = list(args)
        argd.append(kw)
        for dico in argd:
            for var, value in dico.items():
                if var not in self:
                    self.setvar(var, value)

    def merge(self, mergenv):
        """Incorporates key-values from ``mergenv`` into current environment.

        :param Environment mergeenv: The object to be merged in.
        """
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
            logger.debug(
                "Could not find verbose attributes while cloning env..."
            )
        return eclone

    def __enter__(self):
        """Activate the environment when entering a context."""
        self.active(True)
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # @UnusedVariable
        """De-activate the environment on context's exit."""
        self.active(False)

    def native(self, varname):
        """Returns the native form this variable could have in a shell environment."""
        value = self._pool[varname]
        if isinstance(value, str):
            return str(value)
        else:
            return json.dumps(value, cls=ShellEncoder)

    def verbose(self, switch=None, sh=None, fromenv=None):
        """Switch on or off the verbose mode. Returns actual value."""
        if switch is not None:
            self.__dict__["_verbose"] = bool(switch)
        if sh is not None:
            self.__dict__["_sh"] = sh
        return self.__dict__["_verbose"]

    def active(self, *args):
        """
        Bind or unbind current environment to the shell environment according to
        a boolean flag given as first argument.

        Returns current active status after update.
        """
        previous_act = self.osbound()
        osrewind = None
        active = previous_act
        if args and type(args[0]) is bool:
            active = args[0]
        if previous_act and not active and self._os:
            self._record("!!OS_BINDING!!", "Broken...")
            self.__class__._current_active = self._os[-1]
            osrewind = self.__class__._current_active
        if not previous_act and active:
            if self.contextlock is not None and not self.contextlock.active:
                raise RuntimeError(
                    "It's not allowed to switch to an Environment "
                    + "that belongs to an inactive context"
                )
            self._record("!!OS_BINDING!!", "Acquiring...")
            self.__class__._current_active = self
            osrewind = self.__class__._current_active
        if osrewind:
            os.environ.clear()
            for k in filter(
                lambda x: x not in osrewind._noexport, osrewind._pool.keys()
            ):
                os.environ[k] = osrewind.native(k)
        return active

    def naked(self):
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
        return self is self.__class__._current_active

    def tracebacks(self):
        """Dump the stack of manipulations of the current environment."""
        if self.history is not None:
            for u_count, stamp, action in self.history:
                varname, value, stack = action
                print("[", stamp, "]", varname, "=", value, "\n")
                for xs in stack:
                    print(xs)

    def osdump(self):
        """Dump the actual values of the OS environment."""
        for k in sorted(os.environ.keys()):
            print('{:s}="{:s}"'.format(k, os.environ[k]))

    def mydump(self):
        """Dump the actual values of the current environment."""
        for k in sorted(self._pool.keys()):
            print('{:s}="{:s}"'.format(k, str(self._pool[k])))

    def mkautolist(self, prefix):
        """Return a list of variable starting with the ``prefix`` string."""
        return [
            var + '="' + self.get(var, "") + '"'
            for var in self.keys()
            if var.startswith(prefix)
        ]

    def trueshell(self):
        """Extract the actual shell name according to env variable SHELL."""
        return re.sub("^.*/", "", self.getvar("shell"))

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

    def setgenericpath(self, var, value, pos=None):
        """Insert a new path value to a PATH like variable at a given position.

        :param str var: The environment's variable to modify (case insensitive)
        :param str value: The value that will be inserted in the path
        :param int pos: Where in the path, to insert ``value`` (by default, at the end)
        """
        mypath = self.getvar(var).split(":") if self.getvar(var) else []
        value = str(value)
        while value in mypath:
            mypath.remove(value)
        if pos is None:
            pos = len(mypath)
        mypath.insert(pos, value)
        self.setvar(var, ":".join(mypath))

    def rmgenericpath(self, var, value):
        """Remove the specified ``value`` from a PATH like variable."""
        mypath = self.getvar(var).split(":") if self.getvar(var) else []
        while value in mypath:
            mypath.remove(value)
        self.setvar(var, ":".join(mypath))

    def setbinpath(self, value, pos=None):
        """
        Insert a new path ``value`` to the bin search path (i.e. the PATH
        environment variable) at given position.
        """
        self.setgenericpath("PATH", value, pos)

    def rmbinpath(self, value):
        """
        Remove the specified ``value`` from the bin path (i.e. the PATH
        environment variable).
        """
        self.rmgenericpath("PATH", value)


collections.abc.Mapping.register(Environment)


class EnvironmentDeltaContext:
    """Context that will apply a delta on the Environment and rewind it on exit."""

    def __init__(self, env, **kw):
        """
        This object should not be created manually (use the
        :meth:`Environment.delta_context` method instead).
        """
        self._env = env
        self._delta = kw

    def __enter__(self):
        self._env.delta(**self._delta)

    def __exit__(self, exc_type, exc_value, traceback):  # @UnusedVariable
        self._env.rewind()
