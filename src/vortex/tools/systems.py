#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles system interfaces objects that are in charge of
system interaction. Systems objects use the :mod:`footprints` mechanism.

The current active System object should be retrieved using the session's Ticket
(*i.e.* System classes should not be instantiated directly) ::

    t = vortex.ticket()
    sh = t.sh

The System retrieved by this property will always be an instance of subclasses of
:class:`OSExtended`. Consequently, you can safely assume that all attributes,
properties and methods available in :class:`OSExtended` ad :class:`System` are
available to you.

When working with System objects, preferentialy use high-level methods such as
:meth:`~OSExtended.cp`, :meth:`~OSExtended.mv`, :meth:`~OSExtended.rm`,
:meth:`~OSExtended.smartftput`, :meth:`~OSExtended.smartftget`, ...

"""

import filecmp
import glob
import hashlib
import io
import json
import os
import pickle
import platform
import pwd as passwd
import re
import resource
import shutil
import signal
import socket
import stat
import subprocess
import sys
import StringIO
import tarfile
import tempfile
import time
import yaml
from datetime import datetime

import footprints
from opinel.interrupt import SignalInterruptHandler, SignalInterruptError
from opinel.cpus_tool import LinuxCpusInfo
from vortex.gloves import Glove
from vortex.tools import date
from vortex.tools.env import Environment
from vortex.tools.net import StdFtp, AssistedSsh, LinuxNetstats
from vortex.tools.compression import CompressionPipeline
from vortex.util.decorators import nicedeco_plusdoc
from vortex.util.structs import History
from vortex.syntax.stdattrs import DelayedInit

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

#: Pre-compiled regex to check a none str value
isnonedef = re.compile(r'none', re.IGNORECASE)

#: Pre-compiled regex to check a boolean true str value
istruedef = re.compile(r'on|true|ok', re.IGNORECASE)

#: Pre-compiled regex to check a boolean false str value
isfalsedef = re.compile(r'off|false|ko', re.IGNORECASE)


_fmtshcmd_docbonus = """

        This method is decorated by :func:`fmtshcmd`, consequently it accepts
        an additional **fmt** attribute that might alter this method behaviour
        (*i.e.* if a ``thefmt_{name:s}`` method exists (where ``thefmt`` is the
        value of the **ftm** attribute), it will be executed instead of the
        present one).
"""


@nicedeco_plusdoc(_fmtshcmd_docbonus)
def fmtshcmd(func):
    """This decorator gives a try to the equivalent formatted command.

    Example: let ``decomethod`` be a method decorated with the present decorator,
    if a user calls ``decomethod(..., fmt='toto')``, the decorator with look for
    a method called ``toto_decomethod`` : if it exists, it will be used (otherwise,
    the original method is used).
    """
    def formatted_method(self, *args, **kw):
        fmt = kw.pop('fmt', None)
        fmtcall = getattr(self, str(fmt).lower() + '_' + func.func_name, func)
        if getattr(fmtcall, 'func_extern', False):
            return fmtcall(*args, **kw)
        else:
            return fmtcall(self, *args, **kw)
    return formatted_method


def _kw2spawn(func):
    """This decorator justs update the docstring of a class...

    It will state that all **kw** arguments will be passed directly to the
    ```spawn`` method.

    (Because laziness is good and cut&paste is bad)
    """
    func.__doc__ += """

        At some point, all of the **kw** arguments will be passed directly to the
        :meth:`spawn` method. Please see refer to the :meth:`spawn` method
        documentation for more details.
    """
    return func


class ExecutionError(RuntimeError):
    """Go through exception for internal :meth:`OSExtended.spawn` errors."""
    pass


class CdContext(object):
    """
    Context manager for temporarily changing the working directory.

    Returns to the initial directory, even when an exception is raised.
    Has the syntax of system.cd, and can be used through system::

        with sh.cdcontext(newpath, create=True):
            # work in newpath
        # back to the original path
    """

    def __init__(self, sh, newpath, create=False):
        self.sh = sh
        self.create = create
        self.newpath = self.sh.path.expanduser(newpath)

    def __enter__(self):
        self.oldpath = self.sh.getcwd()
        self.sh.cd(self.newpath, create=self.create)

    def __exit__(self, etype, value, traceback):  # @UnusedVariable
        self.sh.cd(self.oldpath)


class System(footprints.FootprintBase):
    """Abstract root class for any :class:`System` subclasses.

    It contains basic generic methods and redefinition of some of the usual
    Python's system methods.
    """

    _abstract = True
    _explicit = False
    _collector = ('system',)

    _footprint = dict(
        info = 'Default system interface',
        attr = dict(
            hostname = dict(
                info = "The computer's network name",
                optional = True,
                default  = platform.node(),
                alias    = ('nodename',)
            ),
            sysname = dict(
                info = "The underlying system/OS name (e.g. Linux, Darwin, ...)",
                optional = True,
                default  = platform.system(),
            ),
            arch = dict(
                info = "The underlying machine type (e.g. i386, x86_64, ...)",
                optional = True,
                default  = platform.machine(),
                alias    = ('machine',)
            ),
            release = dict(
                info = "The underlying system's release, (e.g. 2.2.0, NT, ...)",
                optional = True,
                default  = platform.release()
            ),
            version = dict(
                info = "The underlying system's release version",
                optional = True,
                default  = platform.version()
            ),
            python = dict(
                info = "The Python's version (e.g 2.7.5)",
                optional = True,
                default  = re.sub(r'^(\d+\.\d+\.\d+).*$', r'\1',
                                  platform.python_version())
            ),
            glove = dict(
                info = "The session's Glove object",
                optional = True,
                type     = Glove,
            )
        )
    )

    def __init__(self, *args, **kw):
        """
        In addition to footprint's attributes,  the following attribute may be added:

            * **prompt** - as a starting comment line in :meth:`title` like methods.
            * **trace** - as a boolean to mimic ``set -x`` behaviour (default: *False*).
            * **timer** - time all the calls to external commands (default: *False*).
            * **output** - as a default value for any external spawning command (default: *True*).

        The following attributes are also picked from ``kw`` (by default the
        usual Python's modules are used):

            * **os** - as an alternative to :mod:`os`.
            * **rlimit** - as an alternative to :mod:`resource`.
            * **sh** or **shutil** - as an alternative to :mod:`shutil`.

        **The proxy concept:**

        The :class:`System` class acts as a proxy for the :mod:`os`, :mod:`resource`
        and :mod:`shutil` modules. *i.e.* if a method or attribute
        is not defined in the :class:`System` class, the   :mod:`os`, :mod:`resource`
        and :mod:`shutil` modules are looked-up (in turn): if one of them has
        the desired attribute/method, it is returned.

        Example: let ``sh`` be an object of class :class:`System`, calling
        ``sh.path.exists`` is equivalent to calling ``os.path.exists`` since
        ``path`` is not redefined in the :class:`System` class.

        In vortex, it is mandatory to use the :class:`System` class (and not the
        official Python modules) even for attributes/methods that are not
        redefined. This is not pointless since, in the future, we may decide to
        to redefine a given attribute/method either globally or for a specific
        architecture.

        **Addons:**

        Using the :meth:`extend` method, a :class:`System` object can be extended
        by any object. This mechanism is used by classes deriving from
        :class:`vortex.tools.addons.Addon`.

        Example: let ``sh`` be an object of class :class:`System` and ``MyAddon``
        a subclass of :class:`~vortex.tools.addons.Addon` (of kind 'myaddon') that
        defines the  ``greatstuff`` attribute; creating an object of class
        ``MyAddon`` using ``footprints.proxy.addon(kind='myaddon', shell=sh)``
        will extend the ``sh`` with the ``greatstuff`` attribute (*e.g.* any
        user will be able to call ``sh.greatstuff``).

        """
        logger.debug('Abstract System init %s', self.__class__)
        self.__dict__['_os'] = kw.pop('os', os)
        self.__dict__['_rl'] = kw.pop('rlimit', resource)
        self.__dict__['_sh'] = kw.pop('shutil', kw.pop('sh', shutil))
        self.__dict__['_search'] = [self.__dict__['_os'], self.__dict__['_sh'], self.__dict__['_rl']]
        self.__dict__['_xtrack'] = dict()
        self.__dict__['_history'] = History(tag='shell')
        self.__dict__['_rclast'] = 0
        self.__dict__['prompt'] = kw.pop('prompt', '')
        for flag in ('trace', 'timer'):
            self.__dict__[flag] = kw.pop(flag, False)
        for flag in ('output',):
            self.__dict__[flag] = kw.pop(flag, True)
        super(System, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """The object/class realkind."""
        return 'system'

    @property
    def history(self):
        """The :class:`History` object associated with all :class:`System` objects."""
        return self._history

    @property
    def rclast(self):
        """The last return-code (for external commands)."""
        return self._rclast

    @property
    def search(self):
        """A list of Python's modules that are looked up when an attribute is not found.

        At startup, mod:`os`, :mod:`resource` and :mod:`shutil` are looked up but
        additional Addon classes may be added to this list (see the :meth:`extend`
        method).
        """
        return self._search

    @property
    def default_syslog(self):
        """Address to use in logging.handler.SysLogHandler()."""
        return '/dev/log'

    def extend(self, obj=None):
        """Extend the current external attribute resolution to **obj** (module or object)."""
        if obj is not None:
            if hasattr(obj, 'kind'):
                for k, v in self._xtrack.iteritems():
                    if hasattr(v, 'kind'):
                        if hasattr(self, k):
                            delattr(self, k)
                for addon in self.search:
                    if hasattr(addon, 'kind') and addon.kind == obj.kind:
                        self.search.remove(addon)
            self.search.append(obj)
        return len(self.search)

    def loaded_addons(self):
        """
        Kind of all the loaded :class:`~vortex.tools.addons.Addon objects
        (*i.e.* :class:`~vortex.tools.addons.Addon objects previously
        loaded with the :meth:`extend` method).
        """
        return [addon.kind for addon in self.search if hasattr(addon, 'kind')]

    def external(self, key):
        """Return effective module object reference if any, or *None*."""
        try:
            z = getattr(self, key)  # @UnusedVariable
        except AttributeError:
            pass
        return self._xtrack.get(key, None)

    def __getattr__(self, key):
        """Gateway to undefined method or attributes.

        This is the place where the ``self.search`` list is looked for...
        """
        actualattr = None
        for shxobj in self.search:
            if hasattr(shxobj, key):
                actualattr = getattr(shxobj, key)
                self._xtrack[key] = shxobj
                break
        else:
            raise AttributeError('Method or attribute ' + key + ' not found')
        if callable(actualattr):
            def osproxy(*args, **kw):
                cmd = [key]
                cmd.extend(args)
                cmd.extend(['{0:s}={1:s}'.format(x, str(kw[x])) for x in kw.keys()])
                self.stderr(*cmd)
                return actualattr(*args, **kw)

            osproxy.func_name = key
            osproxy.func_doc = actualattr.__doc__
            osproxy.func_extern = True
            setattr(self, key, osproxy)
            return osproxy
        else:
            return actualattr

    def stderr(self, *args):
        """Write a formatted message to standard error (if ``self.trace == True``)."""
        count, justnow, = self.history.append(*args)
        if self.trace:
            sys.stderr.write(
                "* [{0:s}][{1:d}] {2:s}\n".format(
                    justnow.strftime('%Y/%m/%d-%H:%M:%S'), count,
                    ' '.join([str(x) for x in args])
                )
            )

    def echo(self, args):
        """Joined **args** are echoed."""
        print '>>>', ' '.join(args)

    def title(self, textlist, tchar='=', autolen=96):
        """Formated title output.

        :param list|str testlist: A list of strings that contains the title's text
        :param str tchar: The character used to frame the title text
        :param int autolen: The title width
        """
        if isinstance(textlist, basestring):
            textlist = (textlist,)
        if autolen:
            nbc = autolen
        else:
            nbc = max([len(text) for text in textlist])
        print
        print tchar * (nbc + 4)
        for text in textlist:
            print '{0:s} {1:^{size}s} {0:s}'.format(tchar, text.upper(), size=nbc)
        print tchar * (nbc + 4)
        print ''

    def subtitle(self, text='', tchar='-', autolen=96):
        """Formated subtitle output.

        :param str text: The subtitle's text
        :param str tchar: The character used to frame the title text
        :param int autolen: The title width
        """
        if autolen:
            nbc = autolen
        else:
            nbc = len(text)
        print "\n", tchar * (nbc + 4)
        if text:
            print '# {0:{size}s} #'.format(text, size=nbc)
            print tchar * (nbc + 4)

    def header(self, text='', tchar='-', autolen=False, xline=True, prompt=None):
        """Formated header output.

        :param str text: The subtitle's text
        :param str tchar: The character used to frame the title text
        :param bool autolen: If True the header width will match the text width (10. otherwise)
        :param bool xline: Adds a line of **tchar** after the header text
        :param str prompt: A customised prompt (otherwise ``self.prompt`` is used)
        """
        if autolen:
            nbc = len(prompt + text) + 1
        else:
            nbc = 100
        print "\n", tchar * nbc
        if text:
            if not prompt:
                prompt = self.prompt
            if prompt:
                prompt = str(prompt) + ' '
            else:
                prompt = ''
            print prompt + text
            if xline:
                print tchar * nbc

    def pythonpath(self, output=None):
        """Return or print actual ``sys.path``."""
        if output is None:
            output = self.output
        self.stderr('pythonpath')
        if output:
            return sys.path[:]
        else:
            self.subtitle('Python PATH')
            for pypath in sys.path:
                print pypath
            return True

    @property
    def env(self):
        """Returns the current active environment."""
        return Environment.current()

    def vortex_modules(self, only='.'):
        """Return a filtered list of modules in the vortex package.

        :param str only: The regex used to filter the modules list.
        """
        if self.glove is not None:
            g = self.glove
            mfiles = [
                re.sub(r'^' + mroot + r'/', '', x)
                for mroot in (g.siteroot + '/src', g.siteroot + '/site')
                for x in self.ffind(mroot)
                if self.path.isfile(self.path.join(self.path.dirname(x), '__init__.py'))
            ]
            return [
                re.sub(r'(?:/__init__)?\.py$', '', x).replace('/', '.')
                for x in mfiles
                if (not x.startswith('.') and
                    re.search(only, x, re.IGNORECASE) and
                    x.endswith('.py'))
            ]
        else:
            raise RuntimeError("A glove must be defined")

    def vortex_loaded_modules(self, only='.', output=None):
        """Check loaded modules, producing either a dump or a list of tuple (status, modulename).

        :param str only: The regex used to filter the modules list.
        """
        checklist = list()
        if output is None:
            output = self.output
        for modname in self.vortex_modules(only):
            checklist.append((modname, modname in sys.modules))
        if not output:
            for m, s in checklist:
                print str(s).ljust(8), m
            print '--'
            return True
        else:
            return checklist

    def systems_reload(self):
        """Load extra systems modules not yet loaded."""
        extras = list()
        for modname in self.vortex_modules(only='systems'):
            if modname not in sys.modules:
                try:
                    self.import_module(modname)
                    extras.append(modname)
                except ValueError as err:
                    logger.critical('systems_reload: cannot import module %s (%s)' % (modname, str(err)))
        return extras

    # Redefinition of methods of the resource package...

    def numrlimit(self, r_id):
        """
        Convert actual resource id (**r_id**) in some acceptable *int* for the
        :mod:`resource` module.
        """
        if type(r_id) is not int:
            r_id = r_id.upper()
            if not r_id.startswith('RLIMIT_'):
                r_id = 'RLIMIT_' + r_id
            r_id = getattr(self._rl, r_id, None)
        if r_id is None:
            raise ValueError('Invalid resource specified')
        return r_id

    def setrlimit(self, r_id, r_limits):
        """Proxy to :mod:`resource` function of the same name."""
        self.stderr('setrlimit', r_id, r_limits)
        try:
            r_limits = tuple(r_limits)
        except TypeError:
            r_limits = (r_limits, r_limits)
        return self._rl.setrlimit(self.numrlimit(r_id), r_limits)

    def getrlimit(self, r_id):
        """Proxy to :mod:`resource` function of the same name."""
        self.stderr('getrlimit', r_id)
        return self._rl.getrlimit(self.numrlimit(r_id))

    def getrusage(self, pid=None):
        """Proxy to :mod:`resource` function of the same name with current process as defaut."""
        if pid is None:
            pid = self._rl.RUSAGE_SELF
        self.stderr('getrusage', pid)
        return self._rl.getrusage(pid)


class OSExtended(System):
    """Abstract extended base system.

    It contains many useful Vortex's additions to the usual Python's shell.
    """

    _abstract = True
    _footprint = dict(
        info = 'Abstract extended base system'
    )

    def __init__(self, *args, **kw):
        """
        Before going through parent initialisation (see :class:`System`),
        pickle this attributes:

            * **rmtreemin** - as the minimal depth needed for a :meth:`rmsafe`.
            * **cmpaftercp** - as a boolean for activating full comparison after plain cp (default: *True*).
            * **ftraw** - allows ``smartft*`` methods to use the raw FTP commands
              (e.g. ftget, ftput) instead of the internal Vortex's FTP client
              (default: *False*).
            * **ftputcmd** - The name of the raw FTP command for the "put" action
              (default: ftput).
            * **ftgetcmd** - The name of the raw FTP command for the "get" action
              (default: ftget).
        """
        logger.debug('Abstract System init %s', self.__class__)
        self._rmtreemin = kw.pop('rmtreemin', 3)
        self._cmpaftercp = kw.pop('cmpaftercp', True)
        # Switches for rawft* methods
        self.ftraw = kw.pop('ftraw', False)
        self.ftputcmd = kw.pop('ftputcmd', None)
        self.ftgetcmd = kw.pop('ftgetcmd', None)
        # Some internal variables used by particular methods
        self._ftspool_cache = None
        self._frozen_target = None
        # Go for the superclass' constructor
        super(OSExtended, self).__init__(*args, **kw)
        # Initialise possibly missing objects
        self.__dict__['_cpusinfo'] = None
        self.__dict__['_netstatsinfo'] = None
        # Initialise the signal handler object
        self._signal_intercept_init()

    def target(self, **kw):
        """
        Provide a default :class:`~vortex.tools.targets.Target` according
        to System's own attributes.

        * Extra or alternative attributes may still be provided using **kw**.
        * The object returned by this method will be used in subsequent calls
          to ::attr:`default_target` (this is the concept of frozen target).
        """
        desc = dict(
            hostname=self.hostname,
            sysname=self.sysname
        )
        desc.update(kw)
        self._frozen_target = footprints.proxy.targets.default(**desc)
        return self._frozen_target

    @property
    def default_target(self):
        """Return the latest frozen target."""
        return DelayedInit(self._frozen_target, self.target)

    def popen(self, args, stdin=None, stdout=None, stderr=None, shell=False,
              output=False, bufsize=0):  # @UnusedVariable
        """Return an open pipe for the **args** command.

        :param str|list args: The command (+ its command-line arguments) to be
            executed. When **shell** is *False* it should be a list. When **shell**
            is *True*, it should be a string.
        :param stdin: Specify the input stream characteristics:

            * If *None*, the standard input stream will be opened.
            * If *True*, a pipe is created and data may be sent to the process
              using the :meth:`~subprocess.Popen.communicate` method of the
              returned object.
            * If a File-like object is provided, it will be used as an input stream

        :param stdout: Specify the output stream characteristics:

            * If *None*, the standard output stream is used.
            * If *True*, a pipe is created and standard outputs may be retrieved
              using the :meth:`~subprocess.Popen.communicate` method of the
              returned object.
            * If a File-like object is provided, standard outputs will be written there.

        :param stderr: Specify the error stream characteristics:

            * If *None*, the standard error stream is used.
            * If *True*, a pipe is created and standard errors may be retrieved
              using the :meth:`~subprocess.Popen.communicate` method of the
              returned object.
            * If a File-like object is provided, standard errors will be written there.

        :param bool shell: If *True*, the specified command will be executed
            through the system shell. (It is usually considered a security hazard:
            see the :mod:`subprocess` documentation for more details).
        :param bool output: unused (kept for backward compatibility).
        :param int bufsize: The default buffer size for new pipes (``0`` means unbuffered)
        :return subprocess.Popen: A Python's :class:`~subprocess.Popen` object
            handling the process.
        """
        self.stderr(*args)
        if stdout is True:
            stdout = subprocess.PIPE
        if stdin is True:
            stdin = subprocess.PIPE
        if stderr is True:
            stderr = subprocess.PIPE
        return subprocess.Popen(args, bufsize=bufsize, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell)

    def pclose(self, p, ok=None):
        """Do its best to nicely shutdown the process started by **p**.

        :param subprocess.Popen p: The process to be shutdown
        :param list ok: The shell return codes considered as successful
            (if *None*, only 0 is considered successful)
        :return bool: Returns *True* if the process return code is within the
            **ok** list.
        """
        if p.stdin is not None:
            p.stdin.close()
        p.wait()
        if p.stdout is not None:
            p.stdout.close()
        if p.stderr is not None:
            p.stderr.close()

        try:
            p.terminate()
        except OSError as e:
            if e.errno == 3:
                logger.debug('Processus %s alreaded terminated.' % str(p))
            else:
                raise

        self._rclast = p.returncode
        if ok is None:
            ok = [0]
        if p.returncode in ok:
            return True
        else:
            return False

    def spawn(self, args, ok=None, shell=False, stdin=None, output=None,
              outmode='a', outsplit=True, silent=False, fatal=True,
              taskset=None, taskset_id=0, taskset_bsize=1):
        """Subprocess call of **args**.

        :param str|list args: The command (+ its command-line arguments) to be
            executed. When **shell** is *False* it should be a list. When **shell**
            is *True*, it should be a string.
        :param list ok: The shell return codes considered as successful
            (if *None*, only 0 is considered successful)
        :param bool shell: If *True*, the specified command will be executed
            through the system shell. (It is usually considered a security hazard:
            see the :mod:`subprocess` documentation for more details).
        :param stdin: Specify the input stream characteristics:

            * If *None*, the standard input stream will be opened.
            * If *True*, no standard input will be sent.
            * If a File-like object is provided, it will be used as an input stream.

        :param output: Specify the standard and error stream characteristics:

            * If *None*, ``self.output`` (that defaults to *True*) will be used.
            * If *True*, *stderr* and *stdout* will be captured and *stdout*
              will be returned by the method if the execution goes well
              according to the **ok** list. (see the **outsplit** argument).
            * If *False*, the standard output and error streams will be used.
            * If a File-like object is provided, outputs will be written there.
            * If a string is provided, it's considered to be a filename. The
              file will be opened (see the **outmode** argument) and used to
              redirect *stdout* and *stderr*

        :param str outmode: The open mode of the file output file
            (meaningful only when **output** is a filename).
        :param bools outsplit: It *True*, the captured standard output will be split
            on line-breaks and a list of lines will be returned (with all the
            line-breaks stripped out). Otherwise, the raw standard output text
            is returned. (meaningful only when **output** is *True*).
        :param bool silent: If *True*, in case a bad return-code is encountered
            (according to the **ok** list), the standard error strem is not printed
            out.
        :param bool fatal: It *True*, exceptions will be raised in case of failures
            (more precisely, if a bad return-code is detected (according to the
            **ok** list), an :class:`ExecutionError` is raised). Otherwise, the
            method just returns *False*.
        :param str taskset: If *None*, process will not be binded to a specific
            CPU core (this is usually what we want). Otherwise, **taskset** can be
            a string describing the wanted *topology* and the *method* used to
            bind the process (the string should looks like ``topology_method``).
            (see the :meth:`cpus_affinity_get` method and the
            :mod:`opinel.cpu_tool` module for more details).
        :param int taskset_id: The task id for this process
        :param int taskset_bsize: The number of CPU that will be used (usually 1,
            but possibly more when using threaded programs).
        :note: When a signal is caught by the Python script, the TERM signal is
            sent to the spawned process and then the signal Exception is re-raised
            (the **fatal** argument has no effect on that).
        """
        rc = False
        if ok is None:
            ok = [0]
        if output is None:
            output = self.output
        if stdin is True:
            stdin = subprocess.PIPE
        localenv = os.environ.copy()
        if taskset is not None:
            taskset_def = taskset.split('_')
            taskset, taskset_cmd, taskset_env = self.cpus_affinity_get(taskset_id,
                                                                       taskset_bsize,
                                                                       *taskset_def)
            if taskset:
                localenv.update(taskset_env)
            else:
                logger.warning("CPU binding is not available on this platform")
        if isinstance(args, basestring):
            if taskset:
                args = taskset_cmd + ' ' + args
            if self.timer:
                args = 'time ' + args
            self.stderr(args)
        else:
            if taskset:
                args[:0] = taskset_cmd
            if self.timer:
                args[:0] = ['time']
            self.stderr(*args)
        if isinstance(output, bool):
            if output:
                cmdout, cmderr = subprocess.PIPE, subprocess.PIPE
            else:
                cmdout, cmderr = None, None
        else:
            if isinstance(output, basestring):
                output = open(output, outmode)
            cmdout, cmderr = output, output
        p = None
        try:
            p = subprocess.Popen(args, stdin=stdin, stdout=cmdout, stderr=cmderr,
                                 shell=shell, env=localenv)
            p_out, p_err = p.communicate()
        except ValueError as perr:
            logger.critical(
                'Weird arguments to Popen ({!s}, stdout={!s}, stderr={!s}, shell={!s})'.format(
                    args, cmdout, cmderr, shell
                )
            )
            if fatal:
                raise
            else:
                logger.warning('Carry on because fatal is off')
        except OSError as perr:
            logger.critical('Could not call %s', str(args))
            if fatal:
                raise
            else:
                logger.warning('Carry on because fatal is off')
        except StandardError as perr:
            logger.critical('System returns %s', str(perr))
            if fatal:
                raise RuntimeError('System {!s} spawned {!s} got [{!s}]: {!s}'
                                   .format(self, args, p.returncode, perr))
            else:
                logger.warning('Carry on because fatal is off')
        except (SignalInterruptError, KeyboardInterrupt) as perr:
            logger.critical('The python process was killed: %s. Trying to terminate the subprocess.',
                            str(perr))
            if p:
                if shell:
                    # Kill the process group: apparently it's the only way when shell=T
                    self.killpg(self.getpgid(p.pid), signal.SIGTERM)
                else:
                    p.terminate()
                p.wait()
            raise  # Fatal has no effect on that !
        else:
            if p.returncode in ok:
                if isinstance(output, bool) and output:
                    if outsplit:
                        rc = p_out.rstrip('\n').split('\n')
                    else:
                        rc = p_out
                    p.stdout.close()
                else:
                    rc = not bool(p.returncode)
            else:
                if not silent:
                    logger.warning('Bad return code [%d] for %s', p.returncode, str(args))
                    if isinstance(output, bool) and output:
                        for xerr in p_err:
                            sys.stderr.write(xerr)
                if fatal:
                    raise ExecutionError
                else:
                    logger.warning('Carry on because fatal is off')
        finally:
            self._rclast = p.returncode if p else 1
            if isinstance(output, bool) and p:
                if output:
                    if p.stdout:
                        p.stdout.close()
                    if p.stderr:
                        p.stderr.close()
            elif not isinstance(output, bool):
                output.close()
            del p

        return rc

    def getlogname(self):
        """Be sure to get the actual login name."""
        return passwd.getpwuid(self._os.getuid())[0]

    def getfqdn(self, name=None):
        """
        Return a fully qualified domain name for **name**. Default is to
        check for current *hostname**
        """
        if name is None:
            name = self.default_target.inetname
        return socket.getfqdn(name)

    def pwd(self, output=None):
        """Current working directory."""
        if output is None:
            output = self.output
        self.stderr('pwd')
        realpwd = self._os.getcwd()
        if output:
            return realpwd
        else:
            print realpwd
            return True

    def cd(self, pathtogo, create=False):
        """Change the current working directory to **pathtogo**."""
        pathtogo = self.path.expanduser(pathtogo)
        self.stderr('cd', pathtogo, create)
        if create:
            self.mkdir(pathtogo)
        self._os.chdir(pathtogo)
        return True

    def cdcontext(self, path, create=False):
        """
        Returns a new :class:`CdContext` context manager initialised with the
        **path** and **create** arguments.
        """
        return CdContext(self, path, create)

    def ffind(self, *args):
        """Recursive file find. Arguments are starting paths."""
        if not args:
            args = ['*']
        else:
            args = [self.path.expanduser(x) for x in args]
        files = []
        self.stderr('ffind', *args)
        for pathtogo in self.glob(*args):
            if self.path.isfile(pathtogo):
                files.append(pathtogo)
            else:
                for root, u_dirs, filenames in self._os.walk(pathtogo):  # @UnusedVariable
                    files.extend([self.path.join(root, f) for f in filenames])
        return sorted(files)

    def xperm(self, filename, force=False):
        """Return whether a **filename** exists and is executable or not.

        If **force** is set to *True*, the file's permission will be modified
        so that the file becomes executable.
        """
        if os.path.exists(filename):
            is_x = bool(os.stat(filename).st_mode & 1)
            if not is_x and force:
                self.chmod(filename, os.stat(filename).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                is_x = True
            return is_x
        else:
            return False

    def wperm(self, filename, force=False):
        """Return whether a **filename** exists and is writable by owner or not.

        If **force** is set to *True*, the file's permission will be modified
        so that the file becomes writable.
        """
        if os.path.exists(filename):
            st = os.stat(filename).st_mode
            is_w = bool(st & stat.S_IWUSR)
            if not is_w and force:
                self.chmod(filename, st | stat.S_IWUSR)
                is_w = True
            return is_w
        else:
            return False

    def wpermtree(self, objpath, force=False):
        """Return whether all items are owner-writeable in a hierarchy.

        If **force** is set to *True*, the file's permission of all files in the
        hierarchy will be modified so that they writable.
        """
        rc = self.wperm(objpath, force)
        for dirpath, dirnames, filenames in self.walk(objpath):
            for item in filenames + dirnames:
                rc = self.wperm(self.path.join(dirpath, item), force) and rc
        return rc

    def readonly(self, inodename):
        """Set permissions of the ``inodename`` object to read-only."""
        inodename = self.path.expanduser(inodename)
        self.stderr('readonly', inodename)
        rc = None
        if os.path.exists(inodename):
            if os.path.isdir(inodename):
                rc = self.chmod(inodename, 0555)
            else:
                st = self.stat(inodename).st_mode
                if st & stat.S_IWUSR or st & stat.S_IWGRP or st & stat.S_IWOTH:
                    rc = self.chmod(inodename, st & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
                else:
                    rc = True
        return rc

    def readonlytree(self, objpath):
        """Recursively set permissions of the **objpath** object to read-only."""
        rc = self.readonly(objpath)
        for dirpath, dirnames, filenames in self.walk(objpath):
            for item in filenames + dirnames:
                rc = self.readonly(self.path.join(dirpath, item)) and rc
        return rc

    def usr_file(self, filename):
        """Return whether or not **filename** belongs to the current user."""
        return self._os.stat(filename).st_uid == self._os.getuid()

    def which(self, command):
        """Clone of the eponymous unix command."""
        self.stderr('which', command)
        if command.startswith('/'):
            if self.xperm(command):
                return command
        else:
            for xpath in self.env.path.split(':'):
                fullcmd = os.path.join(xpath, command)
                if self.xperm(fullcmd):
                    return fullcmd

    def touch(self, filename):
        """Clone of the eponymous unix command."""
        filename = self.path.expanduser(filename)
        self.stderr('touch', filename)
        rc = True
        if self.path.exists(filename):
            # Note: "filename" might as well be a directory...
            try:
                os.utime(filename, None)
            except StandardError:
                rc = False
        else:
            fh = file(filename, 'a')
            fh.close()
        return rc

    @fmtshcmd
    def remove(self, objpath):
        """Unlink the specified object (file, directory or directory tree).

        :param str objpath: Path to the object to unlink
        """
        objpath = self.path.expanduser(objpath)
        if os.path.exists(objpath):
            self.stderr('remove', objpath)
            if os.path.isdir(objpath):
                self.rmtree(objpath)
            else:
                self.unlink(objpath)
        else:
            self.stderr('clear', objpath)
        return not os.path.exists(objpath)

    @fmtshcmd
    def rm(self, objpath):
        """Shortcut to :meth:`remove` method.

        :param str objpath: Path to the object to unlink
        """
        return self.remove(objpath)

    def ps(self, opts=None, search=None, pscmd=None):
        """
        Performs a standard process inquiry through :class:`subprocess.Popen`
        and filter the output if a **search** expression is provided (regular
        expressions are used).
        """
        if not pscmd:
            pscmd = ['ps']
        if opts is None:
            opts = []
        pscmd.extend(self._psopts)
        pscmd.extend(opts)
        self.stderr(*pscmd)
        psall = subprocess.Popen(pscmd, stdout=subprocess.PIPE).communicate()[0].split('\n')
        if search:
            psall = filter(lambda x: re.search(search, x), psall)
        return [x.strip() for x in psall]

    def sleep(self, nbsecs):
        """Clone of the unix eponymous command."""
        self.stderr('sleep', nbsecs)
        time.sleep(nbsecs)

    def setulimit(self, r_id):
        """Set an unlimited value to the specified resource (**r_id**)."""
        self.stderr('setulimit', r_id)
        soft, hard = self.getrlimit(r_id)
        soft = min(hard, max(soft, self._rl.RLIM_INFINITY))
        return self.setrlimit(r_id, (soft, hard))

    def ulimit(self):
        """Dump the user limits currently defined."""
        for limit in [r for r in dir(self._rl) if r.startswith('RLIMIT_')]:
            print ' ', limit.ljust(16), ':', self._rl.getrlimit(getattr(self._rl, limit))

    @property
    def cpus_info(self):
        """Return an object of a subclass of  :class:`opinel.cpu_tool.CpusInfo`.

        Such objects are designed to get informations on the platform's CPUs.

        :note: *None* might be returned on some platforms (if cpufinfo is not
            implemented)
        """
        return self._cpusinfo

    def cpus_affinity_get(self, taskid, blocksize=1, method='default', topology='raw'):
        """Get the necessary command/environment to set the CPUs affinity.

        :param int taskid: the task number
        :param int blocksize: the number of thread consumed by one task
        :param str method: The binding method
        :param str topology: The task distribution scheme
        :return: A 3-elements tuple. (bool: BindingPossible,
            list: Starting command prefix, dict: Environment update)
        """
        return (False, list(), dict())

    @property
    def netstatsinfo(self):
        """Return an object of a subclass of :class:`vortex;tools;net.AbstractNetstats`.

        Such objects are designed to get informations on the platform's network
        connection (both TCP and UDP)

        :note: *None* might be returned on some platforms (if netstat is not
            implemented)
        """
        return self._netstatsinfo

    def available_localport(self):
        """Returns an available port number for a new TCP or UDP connection.

        :note: The ``NotImplementedError`` might be raised on some platforms since
            netstat may not be implemented.
        """
        if self.netstatsinfo is None:
            raise NotImplementedError('This function is not implemented on this system.')
        return self.netstatsinfo.available_localport()

    def check_localport(self, port):
        """Check if a **port** number is currently being used.

        :note: The ``NotImplementedError`` might be raised on some platforms since
            netstat may not be implemented.
        """
        if self.netstatsinfo is None:
            raise NotImplementedError('This function is not implemented on this system.')
        return self.netstatsinfo.check_localport(port)

    def clear(self):
        """Clone of the unix eponymous command."""
        self._os.system('clear')

    @property
    def cls(self):
        """Property shortcut to :meth:`clear` screen."""
        self.clear()
        return None

    def rawopts(self, cmdline=None, defaults=None,
                isnone=isnonedef, istrue=istruedef, isfalse=isfalsedef):
        """Parse a simple options command line that looks like `` key=value``.

        :param str cmdline: The command line to be processed (if *None*, ``sys.argv``
            is used to get the script's command line)
        :param dict defaults: defaults values for any missing option.
        :param re.sre_compile isnone: Regex that detects ``None`` values.
        :param re.sre_compile isnone: Regex that detects ``True`` values.
        :param re.sre_compile isnone: Regex that detects ``False`` values.
        :return dict: a dictionary that contains the parsed options (or their defaults)
        """
        opts = dict()
        if defaults:
            try:
                opts.update(defaults)
            except (ValueError, TypeError):
                logger.warning('Could not update options default: %s', defaults)

        if cmdline is None:
            cmdline = sys.argv[1:]
        opts.update(dict([x.split('=') for x in cmdline]))
        for k, v in opts.iteritems():
            if v not in (None, True, False):
                if istrue.match(v):
                    opts[k] = True
                if isfalse.match(v):
                    opts[k] = False
                if isnone.match(v):
                    opts[k] = None
        return opts

    def is_iofile(self, iocandidate):
        """Check if actual **iocandidate** is a valid filename or io stream."""
        return iocandidate is not None and (
            (isinstance(iocandidate, basestring) and self.path.exists(iocandidate)) or
            isinstance(iocandidate, file) or
            isinstance(iocandidate, io.IOBase) or
            isinstance(iocandidate, StringIO.StringIO)
        )

    def ftp(self, hostname, logname=None, delayed=False):
        """Return an :class:`~vortex.tools.net.StdFtp` object.

        :param str hostname: the remote host's name for FTP.
        :param str logname: the logname on the remote host.
        :param bool delayed: delay the actual connection attempt as much as possible.

        See the :class:`~vortex.tools.net.StdFtp` class documentation for
        more information.
        """
        ftpbox = StdFtp(self, hostname)
        if logname is None:
            if self.glove is not None:
                logname = self.glove.user
            else:
                raise ValueError("Either a logname or a glove must be set-up")
        rc = ftpbox.fastlogin(logname, delayed=delayed)
        if rc:
            return ftpbox
        else:
            logger.warning('Could not login on %s as %s [%s]', hostname, logname, str(rc))
            return None

    @fmtshcmd
    def ftget(self, source, destination, hostname=None, logname=None, cpipeline=None):
        """Proceed to a direct ftp get on the specified target (using Vortex's FTP client).

        :param str source: the remote path to get data
        :param destination: The destination of data (either a path to file or a
            File-like object)
        :type destination: str or File-like object
        :param str hostname: The target hostname (default: *None*, see the
            :class:`~vortex.tools.net.StdFtp` class to get the effective default)
        :param str logname: the target logname (default: *None*, see the
            :class:`~vortex.tools.net.StdFtp` class to get the effective default)
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            uncompress the data during the file transfer (default: *None*).
        """
        if isinstance(destination, basestring):  # destination may be Virtual
            self.rm(destination)
        ftp = self.ftp(hostname, logname)
        if ftp:
            if cpipeline is None:
                rc = ftp.get(source, destination)
            else:
                with cpipeline.stream2uncompress(destination) as cdestination:
                    rc = ftp.get(source, cdestination)
            ftp.close()
            return rc
        else:
            return False

    @fmtshcmd
    def ftput(self, source, destination, hostname=None, logname=None, cpipeline=None):
        """Proceed to a direct ftp put on the specified target (using Vortex's FTP client).

        :param source: The source of data (either a path to file or a
            File-like object)
        :type source: str or File-like object
        :param str destination: The path where to upload the data.
        :param str hostname: The target hostname (default: *None*, see the
            :class:`~vortex.tools.net.StdFtp` class to get the effective default)
        :param str logname: the target logname (default: *None*, see the
            :class:`~vortex.tools.net.StdFtp` class to get the effective default)
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            compress the data during the file transfer (default: *None*).
        """
        rc = False
        if self.is_iofile(source):
            ftp = self.ftp(hostname, logname)
            if ftp:
                if cpipeline is None:
                    rc = ftp.put(source, destination)
                else:
                    with cpipeline.compress2stream(source, iosponge=True) as csource:
                        # csource is an IoSponge consequently the size attribute exists
                        rc = ftp.put(csource, destination, size=csource.size)
                ftp.close()
        else:
            raise IOError('No such file or directory: {!r}'.format(source))
        return rc

    def ftspool_cache(self):
        """Return a cache object for the FtSpool."""
        if self._ftspool_cache is None:
            self._ftspool_cache = footprints.proxy.cache(kind='ftstash')
        return self._ftspool_cache

    def copy2ftspool(self, source, nest=False, **kwargs):
        """Make a copy of **source** to the FtSpool cache."""
        h = hashlib.new('md5')
        h.update(source)
        outputname = 'vortex_{:s}_P{:06d}_{:s}'.format(date.now().strftime('%Y%m%d%H%M%S-%f'),
                                                       self.getpid(), h.hexdigest())
        if nest:
            outputname = self.path.join(outputname, self.path.basename(source))
        kwargs['intent'] = 'in'  # Force intent=in
        if self.ftspool_cache().insert(outputname, source, **kwargs):
            return self.ftspool_cache().fullpath(outputname)
        else:
            return False

    def ftserv_put(self, source, destination, hostname=None, logname=None, specialshell=None):
        """Asynchronous put of a file using FtServ."""
        if isinstance(source, basestring) and isinstance(destination, basestring):
            if self.path.exists(source):
                ftcmd = self.ftputcmd or 'ftput'
                extras = list()
                if hostname:
                    extras.extend(['-h', hostname])
                if logname:
                    extras.extend(['-u', logname])
                if specialshell:
                    extras.extend(['-s', specialshell])
                rc = self.spawn([ftcmd,
                                 '-o', 'mkdir',  # Automatically create subdirectories
                                 '-q', ] +  # Asynchronous mode
                                extras + [source, destination], output=False)
            else:
                raise IOError('No such file or directory: {!s}'.format(source))
        else:
            raise IOError('Source or destination is not a plain file path: {!r}'.format(source))
        return rc

    def ftserv_get(self, source, destination, hostname=None, logname=None):
        """Get a file using FtServ."""
        if isinstance(source, basestring) and isinstance(destination, basestring):
            if self.filecocoon(destination):
                destination = self.path.expanduser(destination)
                extras = list()
                if hostname:
                    extras.extend(['-h', hostname])
                if logname:
                    extras.extend(['-u', logname])
                ftcmd = self.ftgetcmd or 'ftget'
                rc = self.spawn([ftcmd, ] + extras + [source, destination], output=False)
            else:
                raise IOError('No such file or directory: {!s}'.format(source))
        else:
            raise IOError('Source or destination is not a plain file path: {!r}'.format(source))
        return rc

    @fmtshcmd
    def rawftput(self, source, destination, hostname=None, logname=None, cpipeline=None):
        """Proceed with some external ftput command on the specified target.

        :param str source: Path to the source filename
        :param str destination: The path where to upload the data.
        :param str hostname: The target hostname  (default: *None*).
        :param str logname: the target logname  (default: *None*).
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            compress the data during the file transfer (default: *None*).
        """
        if cpipeline is not None:
            if cpipeline.compress2rawftp(source):
                return self.ftserv_put(source, destination, hostname, logname,
                                       specialshell=cpipeline.compress2rawftp(source))
            else:
                return self.ftput(source, destination, hostname, logname, cpipeline=cpipeline)
        else:
            return self.ftserv_put(source, destination, hostname, logname)

    def smartftput(self, source, destination, hostname=None, logname=None,
                   cpipeline=None, fmt=None):
        """Select the best alternative between ``ftput`` and ``rawftput``.

        :param source: The source of data (either a path to file or a
            File-like object)
        :type source: str or File-like object
        :param str destination: The path where to upload the data.
        :param str hostname: The target hostname (see :class:`~vortex.tools.net.StdFtp`
            for the default)
        :param str logname: the target logname (see :class:`~vortex.tools.net.StdFtp`
            for the default)
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            compress the data during the file transfer.
        :param str fmt: The format of data.

        ``rawftput`` will be used if all of the following conditions are met:

            * ``self.ftraw`` is *True*
            * **source** is a string (as opposed to a File like object)
            * **destination** is a string (as opposed to a File like object)
        """
        if self.ftraw and isinstance(source, basestring) and isinstance(destination, basestring):
            return self.rawftput(source, destination, hostname=hostname, logname=logname,
                                 cpipeline=cpipeline, fmt=fmt)
        else:
            return self.ftput(source, destination, hostname=hostname, logname=logname,
                              cpipeline=cpipeline, fmt=fmt)

    @fmtshcmd
    def rawftget(self, source, destination, hostname=None, logname=None, cpipeline=None):
        """Proceed with some external ftget command on the specified target.

        :param str source: The remote path to get data
        :param str destination: Path to the filename where to put the data.
        :param str hostname: The target hostname  (default: *None*).
        :param str logname: the target logname  (default: *None*).
        :param CompressionPipeline cpipeline: Unusued (kept for compatibility)
        """
        return self.ftserv_get(source, destination, hostname, logname)

    def smartftget(self, source, destination, hostname=None, logname=None,
                   cpipeline=None, fmt=None):
        """Select the best alternative between ``ftget`` and ``rawftget``.

        :param str source: the remote path to get data
        :param destination: The destination of data (either a path to file or a
            File-like object)
        :type destination: str or File-like object
        :param str hostname: The target hostname (see :class:`~vortex.tools.net.StdFtp`
            for the default)
        :param str logname: the target logname (see :class:`~vortex.tools.net.StdFtp`
            for the default)
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            uncompress the data during the file transfer.
        :param str fmt: The format of data.

        ``rawftget`` will be used if all of the following conditions are met:

            * ``self.ftraw`` is *True*
            * **cpipeline** is None
            * **source** is a string (as opposed to a File like object)
            * **destination** is a string (as opposed to a File like object)
        """
        if (self.ftraw and cpipeline is None and
                isinstance(source, basestring) and isinstance(destination, basestring)):
            # FtServ is uninteresting when dealing with compression
            return self.rawftget(source, destination, hostname=hostname, logname=logname,
                                 cpipeline=cpipeline, fmt=fmt)
        else:
            return self.ftget(source, destination, hostname=hostname, logname=logname,
                              cpipeline=cpipeline, fmt=fmt)

    def ssh(self, hostname, logname=None, *args, **kw):
        """Return an :class:`~vortex.tools.net.AssistedSsh` object.

        :param str hostname: the remote host's name for SSH
        :param str logname: the logname on the remote host

        Parameters provided with **args** or **kw** will be passed diorectly to the
        :class:`~vortex.tools.net.AssistedSsh`  constructor.

        See the :class:`~vortex.tools.net.AssistedSsh` class documentation for
        more information.
        """
        return AssistedSsh(self, hostname, logname, *args, **kw)

    @fmtshcmd
    def scpput(self, source, destination, hostname, logname=None, cpipeline=None):
        """Perform an scp to the specified target.

        :param source: The source of data (either a path to file or a
            File-like object)
        :type source: str or File-like object
        :param str destination: The path where to upload the data.
        :param str hostname: The target hostname.
        :param str logname: the target logname (default: current user)
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            compress the data during the file transfer (default: *None*).
        """
        msg = '[hostname={!s} logname={!s}]'.format(hostname, logname)
        ssh = self.ssh(hostname, logname)
        if isinstance(source, basestring) and cpipeline is None:
            self.stderr('scpput', source, destination, msg)
            return ssh.scpput(source, destination)
        else:
            self.stderr('scpput_stream', source, destination, msg)
            if cpipeline is None:
                return ssh.scpput_stream(source, destination)
            else:
                with cpipeline.compress2stream(source) as csource:
                    return ssh.scpput_stream(csource, destination)

    @fmtshcmd
    def scpget(self, source, destination, hostname, logname=None, cpipeline=None):
        """Perform an scp to get the specified source.

        :param str source: the remote path to get data
        :param destination: The destination of data (either a path to file or a
            File-like object)
        :type destination: str or File-like object
        :param str hostname: The target hostname.
        :param str logname: the target logname (default: current user)
        :param CompressionPipeline cpipeline: If not *None*, the object used to
            uncompress the data during the file transfer (default: *None*).
        """
        msg = '[hostname={!s} logname={!s}]'.format(hostname, logname)
        ssh = self.ssh(hostname, logname)
        if isinstance(destination, basestring) and cpipeline is None:
            self.stderr('scpget', source, destination, msg)
            return ssh.scpget(source, destination)
        else:
            self.stderr('scpget_stream', source, destination, msg)
            if cpipeline is None:
                return ssh.scpget_stream(source, destination)
            else:
                with cpipeline.stream2uncompress(destination) as cdestination:
                    return ssh.scpget_stream(source, cdestination)

    def softlink(self, source, destination):
        """Set a symbolic link if **source** is not **destination**."""
        self.stderr('softlink', source, destination)
        if source == destination:
            return False
        else:
            return self.symlink(source, destination)

    def size(self, filepath):
        """Returns the actual size in bytes of the specified **filepath**."""
        filepath = self.path.expanduser(filepath)
        self.stderr('size', filepath)
        try:
            return self.stat(filepath).st_size
        except StandardError:
            return -1

    def treesize(self, objpath):
        """Size in byte of the whole **objpath** directory (or file).

        Links are not followed, and directory sizes are taken into account:
        should return the same as ``du -sb``.

        Raises ``OSError`` if **objpath** does not exist.
        """
        objpath = self.path.expanduser(objpath)
        if self.path.isdir(objpath):
            total_size = self.size(objpath)
            for dirpath, dirnames, filenames in self.walk(objpath):
                for f in filenames + dirnames:
                    total_size += self.lstat(self.path.join(dirpath, f)).st_size
            return total_size
        return self.lstat(objpath).st_size

    def mkdir(self, dirpath, fatal=True):
        """Normalises path name of **dirpath** and recursively creates this directory."""
        normdir = self.path.normpath(self.path.expanduser(dirpath))
        if normdir and not self.path.isdir(normdir):
            logger.debug('Cocooning directory %s', normdir)
            self.stderr('mkdir', normdir)
            try:
                self.makedirs(normdir)
                return True
            except OSError:
                # The directory may have been created exactly at the same time
                # by another process...
                if fatal and not self.path.isdir(normdir):
                    raise
                return self.path.isdir(normdir)
        else:
            return True

    def filecocoon(self, destination):
        """Normalises path name of ``destination`` and creates **destination**'s directory."""
        return self.mkdir(self.path.dirname(self.path.expanduser(destination)))

    def safe_filesuffix(self):
        """Returns a file suffix that should be unique across the system."""
        return '.'.join((datetime.now().strftime('_%Y%m%d_%H%M%S_%f'),
                         self.hostname, 'p{0:06d}'.format(os.getpid()),))

    def rawcp(self, source, destination):
        """Perform a simple ``copyfile`` or ``copytree`` command depending on **source**.

        When copying a file, the operation is atomic. When copying a directory
        it is not (although the non-atomic portion is very limited).
        """
        source = self.path.expanduser(source)
        destination = self.path.expanduser(destination)
        self.stderr('rawcp', source, destination)
        tmp = destination + self.safe_filesuffix()
        if self.path.isdir(source):
            self.copytree(source, tmp)
            # Warning: Not an atomic portion of code (sorry)
            do_cleanup = self.path.exists(destination)
            if do_cleanup:
                # Move fails if a directory already exists
                self.move(destination, tmp + '.olddir')
            self.move(tmp, destination)
            if do_cleanup:
                self.remove(tmp + '.olddir')
            # End of none atomic part
            return self.path.isdir(destination)
        else:
            self.copyfile(source, tmp)
            # Preserve the execution permissions...
            if self.xperm(source):
                self.xperm(tmp, force=True)
            self.move(tmp, destination)  # Move is atomic for a file
            if self._cmpaftercp:
                return filecmp.cmp(source, destination)
            else:
                return bool(self.size(source) == self.size(destination))

    def hybridcp(self, source, destination, silent=False):
        """Copy the **source** file to a safe **destination**.

        **source** and/or **destination** may be File-like objects.

        If **destination** is a real-word file name (i.e. not e File-like object),
        the operation is atomic.
        """
        self.stderr('hybridcp', source, destination)
        if isinstance(source, basestring):
            if not self.path.exists(source):
                if not silent:
                    logger.error('Missing source %s', source)
                return False
            source = io.open(self.path.expanduser(source), 'rb')
            xsource = True
        else:
            xsource = False
            try:
                source.seek(0)
            except AttributeError:
                logger.warning('Could not rewind io source before cp: ' + str(source))
        if isinstance(destination, basestring):
            if self.filecocoon(destination):
                # Write to a temp file
                original_dest = self.path.expanduser(destination)
                tmp_dest = self.path.expanduser(destination) + self.safe_filesuffix()
                destination = io.open(tmp_dest, 'wb')
                xdestination = True
            else:
                logger.error('Could not create a cocoon for file %s', destination)
                return False
        else:
            destination.seek(0)
            xdestination = False
        rc = self.copyfileobj(source, destination)
        if rc is None:
            rc = True
        if xsource:
            source.close()
        if xdestination:
            destination.close()
            # Move the tmp_file to the real destination
            if not self.move(tmp_dest, original_dest):  # Move is atomic for a file
                logger.error('Cannot move the tmp file to the final destination %s', original_dest)
                return False
        return rc

    def is_samefs(self, path1, path2):
        """Check whether two paths are located on the same filesystem."""
        st1 = self.stat(path1)
        st2 = self.stat(self.path.dirname(self.path.realpath(path2)))
        return st1.st_dev == st2.st_dev and not self.path.islink(path1)

    def smartcp(self, source, destination, silent=False):
        """
        Hard link the **source** file to a safe **destination** (if possible).
        Otherwise, let the standard copy do the job.

        **source** and/or **destination** may be File-like objects.

        When working on a file, the operation is atomic. When working on a
        directory some restrictions apply (see :meth:`rawcp`)
        """
        self.stderr('smartcp', source, destination)
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            return self.hybridcp(source, destination)
        source = self.path.expanduser(source)
        if not self.path.exists(source):
            if not silent:
                logger.error('Missing source %s', source)
            return False
        if self.filecocoon(destination):
            destination = self.path.expanduser(destination)
            if self.path.islink(source):
                # Solve the symbolic link: this may avoid a rawcp
                source = self.path.realpath(source)
            if self.is_samefs(source, destination):
                tmp_destination = destination + self.safe_filesuffix()
                if self.path.isdir(source):
                    rc = self.spawn(['cp', '-al', source, tmp_destination], output=False)
                    self.stderr('chmod', 0444, tmp_destination)
                    oldtrace, self.trace = self.trace, False
                    for linkedfile in self.ffind(tmp_destination):
                        if not self.path.islink(linkedfile):  # This make no sense to chmod symlinks
                            self.chmod(linkedfile, 0444)
                    self.trace = oldtrace
                    if rc:
                        # Warning: Not an atomic portion of code (sorry)
                        do_cleanup = self.path.exists(destination)
                        if do_cleanup:
                            # Move fails if a directory already exists
                            self.move(destination, tmp_destination + '.olddir')
                        rc = self.move(tmp_destination, destination)
                        if do_cleanup:
                            self.remove(tmp_destination + '.olddir')
                        # End of none atomic part
                        if not rc:
                            logger.error('Cannot move the tmp directory to the final destination %s',
                                         destination)
                            self.remove(tmp_destination)  # Anyway, try to clean-up things
                    else:
                        logger.error('Cannot copy the data to the tmp directory %s', tmp_destination)
                        self.remove(tmp_destination)  # Anyway, try to clean-up things
                    return rc
                else:
                    if self.usr_file(source):
                        self.link(source, tmp_destination)
                        self.readonly(tmp_destination)
                        self.move(tmp_destination, destination)  # Move is atomic for a file
                        return self.path.samefile(source, destination)
                    else:
                        rc = self.rawcp(source, destination)
                        if rc:
                            self.readonly(destination)
                        return rc
            else:
                rc = self.rawcp(source, destination)  # Rawcp is atomic as much as possible
                if rc:
                    if self.path.isdir(destination):
                        for copiedfile in self.ffind(destination):
                            if not self.path.islink(copiedfile):  # This make no sense to chmod symlinks
                                self.chmod(copiedfile, 0444)
                    else:
                        self.readonly(destination)
                return rc
        else:
            logger.error('Could not create a cocoon for file %s', destination)
            return False

    @fmtshcmd
    def cp(self, source, destination, intent='inout', smartcp=True, silent=False):
        """Copy the **source** file to a safe **destination**.

        :param source: The source of data (either a path to file or a
            File-like object)
        :type source: str or File-like object
        :param destination: The destination of data (either a path to file or a
            File-like object)
        :type destination: str or File-like object
        :param str intent: 'in' for a read-only copy. 'inout' for a read-write copy
            (default: 'inout').
        :param bool smartcp: use :meth:`smartcp` as much as possible (default: *True*)
        :param bool silent: do not complain on error (default: *False*).

        It relies on :meth:`hybridcp`, :meth:`smartcp` or :meth:`rawcp`
        depending on **source**, **destination** and **intent**.

        The fastest option should be used...
        """
        self.stderr('cp', source, destination)
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            return self.hybridcp(source, destination, silent=silent)
        if not self.path.exists(source):
            if not silent:
                logger.error('Missing source %s', source)
            return False
        if smartcp and intent == 'in':
            return self.smartcp(source, destination, silent=silent)
        if self.filecocoon(destination):
            return self.rawcp(source, destination)
        else:
            logger.error('Could not create a cocoon for file %s', destination)
            return False

    def glob(self, *args):
        """Glob file system entries according to ``args``. Returns a list."""
        entries = []
        for entry in args:
            if entry.startswith(':'):
                entries.append(entry[1:])
            else:
                entries.extend(glob.glob(self.path.expanduser(entry)))
        return entries

    def rmall(self, *args, **kw):
        """Unlink the specified **args** objects with globbing."""
        rc = True
        for pname in args:
            for objpath in self.glob(pname):
                rc = self.remove(objpath, **kw) and rc

    def safepath(self, thispath, safedirs):
        """
        Boolean to check if **thispath** is a subpath of a **safedirs**
        with sufficient depth (or not a subpath at all)
        """
        safe = True
        if len(thispath.split(os.sep)) < self._rmtreemin + 1:
            logger.warning('Unsafe starting point depth %s (min is %s)', thispath, self._rmtreemin)
            safe = False
        else:
            for safepack in safedirs:
                (safedir, d) = safepack
                rp = self.path.relpath(thispath, safedir)
                if not rp.startswith('..'):
                    if len(rp.split(os.sep)) < d:
                        logger.warning('Unsafe access to %s relative to %s', thispath, safedir)
                        safe = False
        return safe

    def rmsafe(self, pathlist, safedirs):
        """
        Recursive unlinks of the specified **pathlist** objects (if safe according
        to :meth:`safepath`).
        """
        ok = True
        if isinstance(pathlist, basestring):
            pathlist = [pathlist]
        for pname in pathlist:
            for entry in filter(lambda x: self.safepath(x, safedirs), self.glob(pname)):
                ok = self.remove(entry) and ok
        return ok

    def _globcmd(self, cmd, args, **kw):
        """Globbing files or directories as arguments before running ``cmd``."""
        cmd.extend([opt for opt in args if opt.startswith('-')])
        cmdlen = len(cmd)
        cmdargs = False
        globtries = [self.path.expanduser(x) for x in args if not x.startswith('-')]
        for pname in globtries:
            cmdargs = True
            cmd.extend(self.glob(pname))
        if cmdargs and len(cmd) == cmdlen:
            logger.warning('Could not find any matching pattern %s', globtries)
            return False
        else:
            kw.setdefault('ok', [0])
            return self.spawn(cmd, **kw)

    @_kw2spawn
    def wc(self, *args, **kw):
        """Word count on globbed files."""
        return self._globcmd(['wc'], args, **kw)

    @_kw2spawn
    def ls(self, *args, **kw):
        """Clone of the eponymous unix command."""
        return self._globcmd(['ls'], args, **kw)

    @_kw2spawn
    def ll(self, *args, **kw):
        """Clone of the eponymous unix alias (ls -l)."""
        kw['output'] = True
        llresult = self._globcmd(['ls', '-l'], args, **kw)
        if llresult:
            for lline in [x for x in llresult if not x.startswith('total')]:
                print lline
        else:
            return False

    @_kw2spawn
    def dir(self, *args, **kw):
        """Proxy to ``ls('-l')``."""
        return self._globcmd(['ls', '-l'], args, **kw)

    @_kw2spawn
    def cat(self, *args, **kw):
        """Clone of the eponymous unix command."""
        return self._globcmd(['cat'], args, **kw)

    @fmtshcmd
    @_kw2spawn
    def diff(self, *args, **kw):
        """Clone of the eponymous unix command."""
        kw.setdefault('ok', [0, 1])
        kw.setdefault('output', False)
        return self._globcmd(['cmp'], args, **kw)

    @_kw2spawn
    def rmglob(self, *args, **kw):
        """Wrapper of the shell's ``rm`` command through the :meth:`globcmd` method."""
        return self._globcmd(['rm'], args, **kw)

    @fmtshcmd
    def move(self, source, destination):
        """Move the ``source`` file or directory (using shutil).

        :param str source: The source object (file, directory, ...)
        :param str destination: The destination object (file, directory, ...)
        """
        self.stderr('move', source, destination)
        try:
            self._sh.move(source, destination)
        except StandardError:
            logger.critical('Could not move <%s> to <%s>', source, destination)
            raise
        else:
            return True

    @fmtshcmd
    def mv(self, source, destination):
        """Move the ``source`` file or directory (using shutil or hybridcp).

        :param source: The source object (file, directory, File-like object, ...)
        :param destination: The destination object (file, directory, File-like object, ...)
        """
        self.stderr('mv', source, destination)
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            self.hybridcp(source, destination)
            if isinstance(source, basestring):
                return self.remove(source)
        else:
            return self.move(source, destination)

    @_kw2spawn
    def mvglob(self, *args):
        """Wrapper of the shell's ``mv`` command through the :meth:`globcmd` method."""
        return self._globcmd(['mv'], args)

    def listdir(self, *args):
        """Proxy to standard :mod:`os` directory listing function."""
        if not args:
            args = ('.',)
        self.stderr('listdir', *args)
        return self._os.listdir(self.path.expanduser(args[0]))

    def l(self, *args):  # @IgnorePep8
        """
        Proxy to globbing after removing any option. A bit like the
        :meth:`ls` method except that that shell's ``ls`` command is not actually
        called.
        """
        rl = [x for x in args if not x.startswith('-')]
        if not rl:
            rl.append('*')
        self.stderr('l', *rl)
        return self.glob(*rl)

    def ldirs(self, *args):
        """
        Proxy to directories globbing after removing any option. A bit like the
        :meth:`ls` method except that that shell's ``ls`` command is not actually
        called.
        """
        rl = [x for x in args if not x.startswith('-')]
        if not rl:
            rl.append('*')
        self.stderr('ldirs', *rl)
        return [x for x in self.glob(*rl) if self.path.isdir(x)]

    @_kw2spawn
    def gzip(self, *args, **kw):
        """Simple gzip compression of a file."""
        cmd = ['gzip', '-vf', args[0]]
        cmd.extend(args[1:])
        return self.spawn(cmd, **kw)

    @_kw2spawn
    def gunzip(self, *args, **kw):
        """Simple gunzip of a gzip-compressed file."""
        cmd = ['gunzip', args[0]]
        cmd.extend(args[1:])
        return self.spawn(cmd, **kw)

    def is_tarfile(self, filename):
        """Return a boolean according to the tar status of the **filename**."""
        return tarfile.is_tarfile(self.path.expanduser(filename))

    def taropts(self, tarfile, opts, verbose=True, autocompress=True):
        """Build a proper string sequence of tar options."""
        zopt = set(opts)
        if verbose:
            zopt.add('v')
        else:
            zopt.discard('v')
        if autocompress:
            if tarfile.endswith('gz'):
                zopt.add('z')
            else:
                zopt.discard('z')
            if tarfile.endswith('bz') or tarfile.endswith('bz2'):
                zopt.add('j')
            else:
                zopt.discard('j')
        return ''.join(zopt)

    @_kw2spawn
    def tar(self, *args, **kw):
        """Create a file archive (always c-something).

        :example: ``self.tar('destination.tar', 'directory1', 'directory2')``
        """
        opts = self.taropts(args[0], 'cf', kw.pop('verbose', True), kw.pop('autocompress', True))
        cmd = ['tar', opts, args[0]]
        cmd.extend(self.glob(*args[1:]))
        return self.spawn(cmd, **kw)

    @_kw2spawn
    def untar(self, *args, **kw):
        """Unpack a file archive (always x-something).

        :example: ``self.untar('source.tar')``
        :example: ``self.untar('source.tar', 'to_untar1', 'to_untar2')``
        """
        opts = self.taropts(args[0], 'xf', kw.pop('verbose', True), kw.pop('autocompress', True))
        cmd = ['tar', opts, args[0]]
        cmd.extend(args[1:])
        return self.spawn(cmd, **kw)

    def smartuntar(self, source, destination, **kw):
        """Unpack a file archive in the appropriate directory.

        If **uniquelevel_ignore** is *True* (default: *False*) and the tar file
        contains only one directory, it will be extracted and renamed to
        **destination**. Otherwise, **destination** will be created and the tar's
        content will be extracted inside it.

        This is done in a relatively safe way since it is checked that no existing
        files/directories are overwritten.
        """
        uniquelevel_ignore = kw.pop('uniquelevel_ignore', False)
        fullsource = self.path.realpath(source)
        self.mkdir(destination)
        loctmp = tempfile.mkdtemp(prefix='untar_', dir=destination)
        with self.cdcontext(loctmp):
            self.untar(fullsource, **kw)
            unpacked = self.glob('*')
            # If requested, ignore the first level of directory
            if (uniquelevel_ignore and len(unpacked) == 1 and
                    self.path.isdir(self.path.join(unpacked[0]))):
                logger.info('Moving contents one level up: %s', unpacked[0])
                unpacked = self.glob(self.path.join(unpacked[0], '*'))
            for untaritem in unpacked:
                itemtarget = self.path.basename(untaritem)
                if self.path.exists('../' + itemtarget):
                    logger.error('Some previous item exists before untar [%s]', untaritem)
                else:
                    self.mv(untaritem, '../' + itemtarget)
        self.rm(loctmp)
        return unpacked

    def is_tarname(self, objname):
        """Check if a ``objname`` is a string with ``.tar`` suffix."""
        return isinstance(objname, basestring) and (objname.endswith('.tar') or
                                                    objname.endswith('.tar.gz') or
                                                    objname.endswith('.tgz') or
                                                    objname.endswith('.tar.bz2') or
                                                    objname.endswith('.tbz'))

    def tarname_radix(self, objname):
        """Remove any ``.tar`` specific suffix."""
        if not self.is_tarname(objname):
            return objname
        radix = self.path.splitext(objname)[0]
        if radix.endswith('.tar'):
            radix = radix[:-4]
        return radix

    def tarfix_in(self, source, destination):
        """Automatically untar **source** if **source** is a tarfile and **destination** is not."""
        ok = True
        if self.is_tarname(source) and not self.is_tarname(destination):
            logger.info('Untar from get <%s>', source)
            (destdir, destfile) = self.path.split(self.path.abspath(destination))
            desttar = self.path.abspath(destination + '.tar')
            self.remove(desttar)
            ok = ok and self.move(destination, desttar)
            loctmp = tempfile.mkdtemp(prefix='untar_', dir=destdir)
            with self.cdcontext(loctmp):
                ok = ok and self.untar(desttar, output=False)
                unpacked = self.glob('*')
                ok = ok and len(unpacked) == 1  # Only one element allowed in this kind of tarfiles
                ok = ok and self.move(unpacked[0], self.path.join(destdir, destfile))
                ok = ok and self.remove(desttar)
            self.rm(loctmp)
        return (ok, source, destination)

    def tarfix_out(self, source, destination):
        """
        Automatically tar the **source** input if **destination** is a tarfile and
        **source** is not."""
        ok = True
        if not self.is_tarname(source) and self.is_tarname(destination):
            logger.info('Tar before put <%s>', source)
            sourcetar = self.path.abspath(source + '.tar')
            (sourcedir, source_rel) = self.path.split(source)
            (sourcedir, sourcefile) = self.path.split(sourcetar)
            with self.cdcontext(sourcedir):
                ok = ok and self.remove(sourcefile)
                ok = ok and self.tar(sourcefile, source_rel, output=False)
            return (ok, sourcetar, destination)
        else:
            return (ok, source, destination)

    def blind_dump(self, gateway, obj, destination, **opts):
        """
        Use **gateway** for a blind dump of the **obj** in file **destination**,
        (either a file descriptor or a filename).
        """
        rc = None
        if hasattr(destination, 'write'):
            rc = gateway.dump(obj, destination, **opts)
        else:
            if self.filecocoon(destination):
                with io.open(self.path.expanduser(destination), 'wb') as fd:
                    rc = gateway.dump(obj, fd, **opts)
        return rc

    def pickle_dump(self, obj, destination, **opts):
        """
        Dump a pickled representation of specified **obj** in file **destination**,
        (either a file descriptor or a filename).
        """
        return self.blind_dump(pickle, obj, destination, **opts)

    def json_dump(self, obj, destination, **opts):
        """
        Dump a json representation of specified **obj** in file **destination**,
        (either a file descriptor or a filename).
        """
        return self.blind_dump(json, obj, destination, **opts)

    def yaml_dump(self, obj, destination, **opts):
        """
        Dump a YAML representation of specified **obj** in file **destination**,
        (either a file descriptor or a filename).
        """
        return self.blind_dump(yaml, obj, destination, **opts)

    def blind_load(self, source, gateway=None):
        """
        Use **gateway** for a blind load the representation stored in file **source**,
        (either a file descriptor or a filename).
        """
        if hasattr(source, 'read'):
            obj = gateway.load(source)
        else:
            with io.open(self.path.expanduser(source), 'rb') as fd:
                if gateway is None:
                    gateway = sys.modules.get(source.split('.')[-1].lower(), yaml)
                obj = gateway.load(fd)
        return obj

    def pickle_load(self, source):
        """
        Load from a pickled representation stored in file **source**,
        (either a file descriptor or a filename).
        """
        return self.blind_load(source, gateway=pickle)

    def json_load(self, source):
        """
        Load from a json representation stored in file **source**,
        (either a file descriptor or a filename).
        """
        return self.blind_load(source, gateway=json)

    def yaml_load(self, source):
        """
        Load from a YAML representation stored in file **source**,
        (either a file descriptor or a filename).
        """
        return self.blind_load(source, gateway=yaml)

    def pickle_clone(self, obj):
        """Clone an object (**obj**) through pickling / unpickling."""
        return pickle.loads(pickle.dumps(obj))

    def utlines(self, *args):
        """Return number of significant code or configuration lines in specified directories."""
        lookfiles = [
            x for x in self.ffind(*args)
            if self.path.splitext[1] in ['.py', '.ini', '.tpl', '.rst']
        ]
        return len([
            x for x in self.cat(*lookfiles)
            if re.search(r'\S', x) and re.search(r'[^\'\"\)\],\s]', x)
        ])

    def _signal_intercept_init(self):
        """Initialise the signal handler object (but do not activate it)."""
        self._sighandler = SignalInterruptHandler()

    def signal_intercept_on(self):
        """Activate the signal's catching.

        See :class:`opinel.interrupt.SignalInterruptHandler` documentation.
        """
        self._sighandler.activate()

    def signal_intercept_off(self):
        """Deactivate the signal's catching.

        See :class:`opinel.interrupt.SignalInterruptHandler` documentation.
        """
        self._sighandler.deactivate()

    _LDD_REGEX = re.compile(r'^\s*([^\s]+)\s+=>\s*([^\s]+)\s+\(0x.+\)$')

    def ldd(self, filename):
        """Call ldd on **filename**.

        Return the mapping between the library name and its physical path.
        """
        if self.path.isfile(filename):
            ldd_out = self.spawn(('ldd', filename))
            libs = dict()
            for ldd_match in [self._LDD_REGEX.match(l) for l in ldd_out]:
                if ldd_match is not None:
                    libs[ldd_match.group(1)] = ldd_match.group(2)
            return libs
        else:
            raise ValueError('{} is not a regular file'.format(filename))

    def generic_compress(self, pipelinedesc, source, destination=None):
        """Compress a file using the :class:`CompressionPipeline` class.

        See the :class:`CompressionPipeline` class documentation for more details.

        :example: "generic_compress('bzip2', 'toto')" will create a toto.bz2 file.
        """
        cp = CompressionPipeline(self, pipelinedesc)
        if destination is None:
            if isinstance(source, basestring):
                destination = source + cp.suffix
            else:
                raise ValueError("If destination is omitted, source must be a filename.")
        return cp.compress2file(source, destination)

    def generic_uncompress(self, pipelinedesc, source, destination=None):
        """Uncompress a file using the :class:`CompressionPipeline` class.

        See the :class:`CompressionPipeline` class documentation for more details.

        :example: "generic_uncompress('bzip2', 'toto.bz2')" will create a toto file.
        """
        cp = CompressionPipeline(self, pipelinedesc)
        if destination is None:
            if isinstance(source, basestring):
                if source.endswith(cp.suffix):
                    destination = source[:-len(cp.suffix)]
                else:
                    raise ValueError("Source do not exhibit the appropriate suffix ({:s})".format(cp.suffix))
            else:
                raise ValueError("If destination is omitted, source must be a filename.")
        return cp.file2uncompress(source, destination)


class Python27(object):
    """Python features starting from version 2.7."""

    def import_module(self, modname):
        """Import the module named **modname** with :mod:`importlib` package."""
        try:
            import importlib
        except ImportError:
            logger.critical('Could not load importlib')
            raise
        except Exception:
            logger.critical('Unexpected error: %s', sys.exc_info()[0])
            raise
        else:
            importlib.import_module(modname)
        return sys.modules.get(modname)

    def import_function(self, funcname):
        """Import the function named **funcname** qualified by a proper module name package."""
        thisfunc = None
        if '.' in funcname:
            thismod = self.import_module('.'.join(funcname.split('.')[:-1]))
            if thismod:
                thisfunc = getattr(thismod, funcname.split('.')[-1], None)
        else:
            logger.error('Bad function path name <%s>' % funcname)
        return thisfunc


class Garbage(OSExtended, Python27):
    """
    Default system class for weird systems.

    Hopefully an extended system will be loaded later on...
    """

    _footprint = dict(
        info = 'Garbage base system',
        attr = dict(
            sysname = dict(
                outcast = ['Linux', 'Darwin']
            )
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT
        )
    )

    def __init__(self, *args, **kw):
        """Gateway to parent method after debug logging."""
        logger.debug('Garbage system init %s', self.__class__)
        super(Garbage, self).__init__(*args, **kw)


class Linux(OSExtended):
    """Abstract default system class for most Linux based systems."""

    _abstract = True
    _footprint = dict(
        info = 'Abstract Linux base system',
        attr = dict(
            sysname = dict(
                values = ['Linux']
            )
        )
    )

    def __init__(self, *args, **kw):
        """
        Before going through parent initialisation (see :class:`OSExtended`),
        pickle this attributes:

            * **psopts** - as default option for the ps command (default: ``-w -f -a``).
        """
        logger.debug('Linux system init %s', self.__class__)
        self._psopts = kw.pop('psopts', ['-w', '-f', '-a'])
        super(Linux, self).__init__(*args, **kw)
        self.__dict__['_cpusinfo'] = LinuxCpusInfo()
        self.__dict__['_netstatsinfo'] = LinuxNetstats()

    @property
    def realkind(self):
        return 'linux'

    def cpus_affinity_get(self, taskid, blocksize=1, topology='socketpacked', method='taskset'):
        """Get the necessary command/environment to set the CPUs affinity.

        :param int taskid: the task number
        :param int blocksize: the number of thread consumed by one task
        :param str method: The binding method
        :param str topology: The task distribution scheme
        :return: A 3-elements tuple. (bool: BindingPossible,
            list: Starting command prefix, dict: Environment update)
        """
        if method not in ('taskset', 'gomp'):
            raise ValueError('Unknown binding method ({:s}).'.format(method))
        if method == 'taskset':
            if not self.which('taskset'):
                logger.warning("The taskset is program is missing. Going on without binding.")
                return (False, list(), dict())
        try:
            cpulist = getattr(self.cpus_info, topology + '_cpulist')(blocksize)
        except AttributeError:
            raise ValueError('Unknown topology ({:s}).'.format(topology))
        cpulist = list(cpulist)
        cpus = [cpulist[(taskid * blocksize + i) % len(cpulist)]
                for i in range(blocksize)]
        cmdl = list()
        env = dict()
        if method == 'taskset':
            cmdl += ['taskset', '--cpu-list', ','.join([str(c) for c in cpus])]
        elif method == 'gomp':
            env['GOMP_CPU_AFFINITY'] = ' '.join([str(c) for c in cpus])
        return (True, cmdl, env)


class Linux27(Linux, Python27):
    """Linux system with python version >= 2.7"""

    _footprint = dict(
        info = 'Linux based system with aging Python version',
        attr = dict(
            python = dict(
                values = ['2.7.' + str(x) for x in range(3, 50)]
            )
        )
    )


class LinuxDebug(Linux27):
    """Special system class for crude debugging on Linux based systems."""

    _footprint = dict(
        info = 'Linux debug system',
        attr = dict(
            version = dict(
                optional = False,
                values = ['dbug', 'debug'],
                remap = dict(
                    dbug = 'debug'
                )
            )
        )
    )

    def __init__(self, *args, **kw):
        """Gateway to parent method after debug logging."""
        logger.debug('LinuxDebug system init %s', self.__class__)
        super(LinuxDebug, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'linuxdebug'


class Macosx(OSExtended, Python27):
    """Mac under MacOSX."""

    _footprint = dict(
        info = 'Apple Mac computer under Macosx with aging Python version',
        attr = dict(
            sysname = dict(
                values = ['Darwin']
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    def __init__(self, *args, **kw):
        """
        Before going through parent initialisation (see :class:`OSExtended`),
        pickle this attributes:

            * **psopts** - as default option for the ps command (default: ``-w -f -a``).
        """
        logger.debug('Darwin system init %s', self.__class__)
        self._psopts = kw.pop('psopts', ['-w', '-f', '-a'])
        super(Macosx, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'darwin'

    @property
    def default_syslog(self):
        """Address to use in logging.handler.SysLogHandler()."""
        return '/var/run/syslog'
