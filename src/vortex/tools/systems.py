#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles system interfaces objects that are in charge of
system interaction. Systems objects use the :mod:`footprints` mechanism.
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
from datetime import datetime

import footprints
from opinel.interrupt import SignalInterruptHandler, SignalInterruptError
from vortex.gloves import Glove
from vortex.tools import date
from vortex.tools.env import Environment
from vortex.tools.net import StdFtp
from vortex.util.decorators import nicedeco
from vortex.util.structs import History

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

#: Pre-compiled regex to check a none str value
isnonedef = re.compile(r'none', re.IGNORECASE)

#: Pre-compiled regex to check a boolean true str value
istruedef = re.compile(r'on|true|ok', re.IGNORECASE)

#: Pre-compiled regex to check a boolean false str value
isfalsedef = re.compile(r'off|false|ko', re.IGNORECASE)


@nicedeco
def fmtshcmd(func):
    """This decorator give a try to the equivalent formatted command."""

    def formatted_method(self, *args, **kw):
        fmt = kw.pop('fmt', None)
        fmtcall = getattr(self, str(fmt).lower() + '_' + func.func_name, func)
        if getattr(fmtcall, 'func_extern', False):
            return fmtcall(*args, **kw)
        else:
            return fmtcall(self, *args, **kw)

    return formatted_method


class ExecutionError(RuntimeError):
    """Go through exception for internal :meth:`spawn` errors."""
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
        self.oldath = self.sh.getcwd()
        self.sh.cd(self.newpath, create=self.create)

    def __exit__(self, etype, value, traceback):
        self.sh.cd(self.oldath)


class System(footprints.FootprintBase):
    """
    Root class for any :class:`System` subclasses.
    """

    _abstract  = True
    _explicit  = False
    _collector = ('system',)

    _footprint = dict(
        info = 'Default information system',
        attr = dict(
            hostname = dict(
                optional = True,
                default  = platform.node(),
                alias    = ('nodename',)
            ),
            sysname = dict(
                optional = True,
                default  = platform.system(),
            ),
            arch = dict(
                optional = True,
                default  = platform.machine(),
                alias    = ('machine',)
            ),
            release = dict(
                optional = True,
                default  = platform.release()
            ),
            version = dict(
                optional = True,
                default  = platform.version()
            ),
            python = dict(
                optional = True,
                default  = re.sub(r'^(\d+\.\d+\.\d+).*$', r'\1',
                                  platform.python_version())
            ),
            glove = dict(
                optional = True,
                type     = Glove,
            )
        )
    )

    def __init__(self, *args, **kw):
        """
        Before going through parent initialisation, pickle this attributes:
          * os - as an alternativer to :mod:`os`.
          * sh - as an alternativer to :mod:`shutil`.
          * prompt - as a starting comment line in :meth:`title` like methods.
          * trace - as a boolean to mimic ``set -x`` behavior (default: False).
          * output - as a default value for any external spawning command (default: True).
        """
        logger.debug('Abstract System init %s', self.__class__)
        self.__dict__['_os']      = kw.pop('os', os)
        self.__dict__['_rl']      = kw.pop('rlimit', resource)
        self.__dict__['_sh']      = kw.pop('shutil', kw.pop('sh', shutil))
        self.__dict__['_search']  = [self.__dict__['_os'], self.__dict__['_sh'], self.__dict__['_rl']]
        self.__dict__['_xtrack']  = dict()
        self.__dict__['_history'] = History(tag='shell')
        self.__dict__['_rclast']  = 0
        self.__dict__['prompt']   = ''
        for flag in ('trace', 'timer'):
            self.__dict__[flag] = kw.pop(flag, False)
        for flag in ('output',):
            self.__dict__[flag] = kw.pop(flag, True)
        super(System, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'system'

    @property
    def history(self):
        return self._history

    @property
    def rclast(self):
        return self._rclast

    @property
    def search(self):
        return self._search

    @property
    def default_syslog(self):
        """Address to use in logging.handler.SysLogHandler()."""
        return '/dev/log'

    def extend(self, obj=None):
        """Extend the current external attribute resolution to ``obj`` (module or object)."""
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
        return [addon.kind for addon in self.search if hasattr(addon, 'kind')]

    def external(self, key):
        """Return effective module object reference if any, or None."""
        try:
            z = getattr(self, key)
        except AttributeError:
            pass
        return self._xtrack.get(key, None)

    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in ``_os`` or ``_sh`` internals."""
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
        """Write a formatted message to standard error."""
        count, justnow, = self.history.append(*args)
        if self.trace:
            sys.stderr.write(
                "* [{0:s}][{1:d}] {2:s}\n".format(
                    justnow.strftime('%Y/%m/%d-%H:%M:%S'), count,
                    ' '.join([str(x) for x in args])
                )
            )

    def getfqdn(self, name=None):
        """Return a fully qualified domain name for ``name``. Default is to check for current ``hostname``."""
        if name is None:
            name = self.target().inetname
        return socket.getfqdn(name)

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
        """Change directory to ``pathtogo``."""
        pathtogo = self.path.expanduser(pathtogo)
        self.stderr('cd', pathtogo, create)
        if create:
            self.mkdir(pathtogo)
        self._os.chdir(pathtogo)
        return True

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
                for root, u_dirs, filenames in self._os.walk(pathtogo):
                    files.extend([self.path.join(root, f) for f in filenames])
        return sorted(files)

    @property
    def env(self):
        """Returns the current active environment."""
        return Environment.current()

    def echo(self, args):
        """Joined args are echoed."""
        print '>>>', ' '.join(args)

    def title(self, textlist, tchar='=', autolen=96):
        """Formated title output."""
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
        """Formated subtitle output."""
        if autolen:
            nbc = autolen
        else:
            nbc = len(text)
        print "\n", tchar * (nbc + 4)
        if text:
            print '# {0:{size}s} #'.format(text, size=nbc)
            print tchar * (nbc + 4)

    def header(self, text='', tchar='-', autolen=False, xline=True, prompt=None):
        """Formated subtitle output."""
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

    def xperm(self, filename, force=False):
        """Return whether a file exists and is executable or not."""
        if os.path.exists(filename):
            is_x = bool(os.stat(filename).st_mode & 1)
            if not is_x and force:
                self.chmod(filename, os.stat(filename).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                is_x = True
            return is_x
        else:
            return False

    def wperm(self, filename, force=False):
        """Return whether a file exists and is writable by owner or not."""
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
        """Return whether all items are owner-writeable in a hierarchy."""
        rc = self.wperm(objpath, force)
        for dirpath, dirnames, filenames in self.walk(objpath):
            for item in filenames + dirnames:
                rc = self.wperm(self.path.join(dirpath, item), force) and rc
        return rc

    def which(self, command):
        """Clone of the unix command."""
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
        """Clone of the unix command."""
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
        """Unlink the specified object (file or directory)."""
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
        """Shortcut to :meth:`remove` method (file or directory)."""
        return self.remove(objpath)

    def ps(self, opts=None, search=None, pscmd=None):
        """
        Performs a standard process inquiry through :class:`subprocess.Popen`
        and filter the output if a ``search`` expression is provided.
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

    def readonly(self, inodename):
        """Set permissions of the ``filename`` object to read-only."""
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
        """Recursively set permissions of the ``dirname`` object to read-only."""
        rc = self.readonly(objpath)
        for dirpath, dirnames, filenames in self.walk(objpath):
            for item in filenames + dirnames:
                rc = self.readonly(self.path.join(dirpath, item)) and rc
        return rc

    def sleep(self, nbsecs):
        """Clone of the unix command."""
        self.stderr('sleep', nbsecs)
        time.sleep(nbsecs)

    def vortex_modules(self, only='.'):
        """Return a filtered list of modules in the vortex package."""
        if self.glove is not None:
            g = self.glove
            mfiles = [
                re.sub(r'^' + mroot + r'/', '', x)
                for mroot in (g.siteroot + '/src', g.siteroot + '/site')
                for x in self.ffind(mroot)
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
        """Check loaded modules, producing either a dump or a list of tuple (status, modulename)."""
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

    def popen(self, args, stdin=None, stdout=None, stderr=None, shell=False, output=False, bufsize=0):
        """Return an open pipe on output of args command."""
        self.stderr(*args)
        if stdout is True:
            stdout = subprocess.PIPE
        if stdin is True:
            stdin = subprocess.PIPE
        if stderr is True:
            stderr = subprocess.PIPE
        return subprocess.Popen(args, bufsize=bufsize, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell)

    def pclose(self, p, ok=None):
        """Do its best to nicely opened pipe command linked to arg ``p``."""
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
              outmode='a', outsplit=True, silent=False, fatal=True):
        """Subprocess call of ``args``."""
        rc = False
        if ok is None:
            ok = [0]
        if output is None:
            output = self.output
        if stdin is True:
            stdin = subprocess.PIPE
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
            p = subprocess.Popen(args, stdin=stdin, stdout=cmdout, stderr=cmderr, shell=shell)
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

    def numrlimit(self, r_id):
        """Convert actual resource id in some acceptable int for module :mod:`resource`."""
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

    def setulimit(self, r_id):
        """Set an unlimited value to resource specified."""
        self.stderr('setulimit', r_id)
        soft, hard = self.getrlimit(r_id)
        soft = min(hard, max(soft, self._rl.RLIM_INFINITY))
        return self.setrlimit(r_id, (soft, hard))

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

    def ulimit(self):
        """Dump the user limits currently defined."""
        for limit in [r for r in dir(self._rl) if r.startswith('RLIMIT_')]:
            print ' ', limit.ljust(16), ':', self._rl.getrlimit(getattr(self._rl, limit))

    def getlogname(self):
        """Be sure to get actual login name."""
        return passwd.getpwuid(self._os.getuid())[0]

    def cdcontext(self, path, create=False):
        return CdContext(self, path, create)


class OSExtended(System):

    _abstract = True
    _footprint = dict(
        info = 'Extended base system'
    )

    def __init__(self, *args, **kw):
        """
        Before going through parent initialisation, pickle this attributes:

          * rmtreemin - as the minimal depth needed for a :meth:`rmsafe`.
          * cmpaftercp - as a boolean for activating full comparison after plain cp (default: True).
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
        # Go for the superclass' constructor
        super(OSExtended, self).__init__(*args, **kw)
        # Intialiase the signal handler object
        self._signal_intercept_init()

    def target(self, **kw):
        """Provide a default target according to system own attributes."""
        desc = dict(
            hostname = self.hostname,
            sysname  = self.sysname
        )
        desc.update(kw)
        self._frozen_target = footprints.proxy.targets.default(**desc)
        return self._frozen_target

    def clear(self):
        """Clear screen."""
        self._os.system('clear')

    @property
    def cls(self):
        """Property shortcut to clear screen."""
        self.clear()
        return None

    def rawopts(self, cmdline=None, defaults=None, isnone=isnonedef, istrue=istruedef, isfalse=isfalsedef):
        """Parse a simple options command line as key=value."""
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
        """Check if actual candidate is a valid filename or io stream."""
        return iocandidate is not None and (
            (isinstance(iocandidate, basestring) and self.path.exists(iocandidate)) or
            isinstance(iocandidate, io.IOBase) or
            isinstance(iocandidate, StringIO.StringIO)
        )

    def ftp(self, hostname, logname=None):
        """Returns an open ftp session on the specified target."""
        ftpbox = StdFtp(self, hostname)
        if logname is None:
            if self.glove is not None:
                logname = self.glove.user
            else:
                raise ValueError("Either a logname or a glove must be set-up")
        rc = ftpbox.fastlogin(logname)
        if rc:
            return ftpbox
        else:
            logger.warning('Could not login on %s as %s [%s]', hostname, logname, str(rc))
            return None

    @fmtshcmd
    def ftget(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        if isinstance(destination, basestring):  # destination may be Virtual
            self.rm(destination)
        ftp = self.ftp(hostname, logname)
        if ftp:
            rc = ftp.get(source, destination)
            ftp.close()
            return rc
        else:
            return False

    @fmtshcmd
    def ftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp put on the specified target."""
        rc = False
        if self.is_iofile(source):
            ftp = self.ftp(hostname, logname)
            if ftp:
                rc = ftp.put(source, destination)
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
        """Make a copy of **source** to the FtSpool directory."""
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
        """Asynchrone put of a file using FtServ."""
        rc = False
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
    def rawftput(self, source, destination, hostname=None, logname=None):
        """Proceed with some external ftput command on the specified target."""
        return self.ftserv_put(source, destination, hostname, logname)

    def smartftput(self, source, destination, hostname=None, logname=None, fmt=None):
        """Proceed some ftput or rawftput."""
        if self.ftraw and isinstance(source, basestring) and isinstance(destination, basestring):
            return self.rawftput(source, destination, hostname=hostname, logname=logname, fmt=fmt)
        else:
            return self.ftput(source, destination, hostname=hostname, logname=logname, fmt=fmt)

    @fmtshcmd
    def rawftget(self, source, destination, hostname=None, logname=None):
        """Proceed with some external ftget command on the specified target."""
        return self.ftserv_get(source, destination, hostname, logname)

    def smartftget(self, source, destination, hostname=None, logname=None, fmt=None):
        """Proceed some ftget or rawftget."""
        if self.ftraw and isinstance(source, basestring) and isinstance(destination, basestring):
            return self.rawftget(source, destination, hostname=hostname, logname=logname, fmt=fmt)
        else:
            return self.ftget(source, destination, hostname=hostname, logname=logname, fmt=fmt)

    def softlink(self, source, destination):
        """Set a symbolic link if source is not destination."""
        self.stderr('softlink', source, destination)
        if source == destination:
            return False
        else:
            return self.symlink(source, destination)

    def filecocoon(self, destination):
        """Normalizes path name of the ``destination`` and creates this directory."""
        return self.mkdir(self.path.dirname(self.path.expanduser(destination)))

    def size(self, filepath):
        """Returns the actual size in bytes of the specified ``filepath``."""
        filepath = self.path.expanduser(filepath)
        self.stderr('size', filepath)
        try:
            return self.stat(filepath).st_size
        except StandardError:
            return -1

    def treesize(self, objpath):
        """Size in byte of the whole directory (or file).
           Links are not followed, and directory sizes are taken
           into account: should return the same as ``du -sb``.
           Raises OSError if objpath does not exist.
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
        """Normalizes path name and recursively creates this directory."""
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

    def safe_filesuffix(self):
        """return a file suffix that should be unique across the system"""
        return '.'.join((datetime.now().strftime('_%Y%m%d_%H%M%S_%f'),
                         self.hostname, 'p{0:06d}'.format(os.getpid()),))

    def rawcp(self, source, destination):
        """Perform a simple ``copyfile`` or ``copytree`` command.

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
            self.move(tmp, destination)  # Move is atomic for a file
            if self._cmpaftercp:
                return filecmp.cmp(source, destination)
            else:
                return bool(self.size(source) == self.size(destination))

    def hybridcp(self, source, destination):
        """
        Copy the ``source`` file to a safe ``destination``.

        ``source`` and/or ``destination`` may be File-like objects. If
        ``destination`` is a realword file name (i.e. not e File-like object),
        the operation is atomic.
        """
        self.stderr('hybridcp', source, destination)
        if isinstance(source, basestring):
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
        """Check whether two paths are on the same filesystem."""
        st1 = self.stat(path1)
        st2 = self.stat(self.path.dirname(self.path.realpath(path2)))
        return st1.st_dev == st2.st_dev and not self.path.islink(path1)

    def smartcp(self, source, destination):
        """
        Hard link the ``source`` file to a safe ``destination`` if possible.
        Otherwise, let the standard copy do the job.

        When working on a file, the operation is atomic. When working on a
        directory some restrictions apply (see :meth:`rawcp`)
        """
        self.stderr('smartcp', source, destination)
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            return self.hybridcp(source, destination)
        source = self.path.expanduser(source)
        if not self.path.exists(source):
            logger.error('Missing source %s', source)
            return False
        if self.filecocoon(destination):
            destination = self.path.expanduser(destination)
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
                    self.link(source, tmp_destination)
                    self.readonly(tmp_destination)
                    self.move(tmp_destination, destination)  # Move is atomic for a file
                    return self.path.samefile(source, destination)
            else:
                rc = self.rawcp(source, destination)  # Rawcp is atomic as much as possiblr
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
    def cp(self, source, destination, intent='inout', smartcp=True):
        """Copy the ``source`` file to a safe ``destination``.

        It relies on :meth:`hybridcp`, :meth:`smartcp` or :meth:`rawcp`
        depending on ``source``, ``destination`` and ``intent``.
        """
        self.stderr('cp', source, destination)
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            return self.hybridcp(source, destination)
        if not self.path.exists(source):
            logger.error('Missing source %s', source)
            return False
        if smartcp and intent == 'in':
            return self.smartcp(source, destination)
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
        """Unlink the specified `args` objects with globbing."""
        rc = True
        for pname in args:
            for objpath in self.glob(pname):
                rc = self.remove(objpath, **kw) and rc

    def safepath(self, thispath, safedirs):
        """
        Boolean to check if :var:``thispath`` is a subpath of a safedir
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
                        logger.warning('Unsafe acces to %s relative to %s', thispath, safedir)
                        safe = False
        return safe

    def rmsafe(self, pathlist, safedirs):
        """Recursive unlinks the specified `args` objects if safe."""
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

    def wc(self, *args, **kw):
        """Word count on globbed files."""
        return self._globcmd(['wc'], args, **kw)

    def ls(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        return self._globcmd(['ls'], args, **kw)

    def ll(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        kw['output'] = True
        llresult = self._globcmd(['ls', '-l'], args, **kw)
        if llresult:
            for lline in [x for x in llresult if not x.startswith('total')]:
                print lline
        else:
            return False

    def dir(self, *args, **kw):
        """Proxy to ``ls('-l')``."""
        return self._globcmd(['ls', '-l'], args, **kw)

    def cat(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        return self._globcmd(['cat'], args, **kw)

    @fmtshcmd
    def diff(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        kw.setdefault('ok', [0, 1])
        kw.setdefault('output', False)
        return self._globcmd(['cmp'], args, **kw)

    def rmglob(self, *args, **kw):
        """Wrapper of the ``rm`` command through the globcmd."""
        return self._globcmd(['rm'], args, **kw)

    @fmtshcmd
    def move(self, source, destination):
        """Move the ``source`` file or directory."""
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
        """Shortcut to :meth:`move` method (file or directory)."""
        self.stderr('mv', source, destination)
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            self.hybridcp(source, destination)
            if isinstance(source, basestring):
                return self.remove(source)
        else:
            return self.move(source, destination)

    def mvglob(self, *args):
        """Wrapper of the ``mv`` command through the globcmd."""
        return self._globcmd(['mv'], args)

    def listdir(self, *args):
        """Proxy to standard :mod:`os` directory listing function."""
        if not args:
            args = ('.',)
        self.stderr('listdir', *args)
        return self._os.listdir(self.path.expanduser(args[0]))

    def l(self, *args):
        """Proxy to globbing after removing any option. A bit like :meth:`ls` method."""
        rl = [x for x in args if not x.startswith('-')]
        if not rl:
            rl.append('*')
        self.stderr('l', *rl)
        return self.glob(*rl)

    def ldirs(self, *args):
        """Proxy to directories globbing after removing any option. A bit like :meth:`ls` method."""
        rl = [x for x in args if not x.startswith('-')]
        if not rl:
            rl.append('*')
        self.stderr('ldirs', *rl)
        return [x for x in self.glob(*rl) if self.path.isdir(x)]

    def is_tarfile(self, filename):
        """Return a boolean according to the tar status of the ``filename``."""
        return tarfile.is_tarfile(self.path.expanduser(filename))

    def taropts(self, tarfile, opts, verbose=True):
        """Build a proper string sequence of tar options."""
        zopt = set(opts)
        if verbose:
            zopt.add('v')
        else:
            zopt.discard('v')
        if tarfile.endswith('gz'):
            zopt.add('z')
        else:
            zopt.discard('z')
        if tarfile.endswith('bz') or tarfile.endswith('bz2'):
            zopt.add('j')
        else:
            zopt.discard('j')
        return ''.join(zopt)

    def tar(self, *args, **kw):
        """Create a file archive (always c-something)'"""
        cmd = ['tar', self.taropts(args[0], 'cf', kw.pop('verbose', True)), args[0]]
        cmd.extend(self.glob(*args[1:]))
        return self.spawn(cmd, **kw)

    def untar(self, *args, **kw):
        """Unpack a file archive (always x-something)'"""
        cmd = ['tar', self.taropts(args[0], 'xf', kw.pop('verbose', True)), args[0]]
        cmd.extend(args[1:])
        return self.spawn(cmd, **kw)

    def smartuntar(self, source, destination, **kw):
        """Unpack a file archive in the appropriate directory."""
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
        return isinstance(objname, str) and (objname.endswith('.tar') or
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
        """Untar the ``destination`` if ``source`` is a tarfile."""
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
        """Tar the ``source`` input."""
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
        Use ``gateway`` for a blind dump of the ``obj`` in file ``destination``,
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
        Dump a pickled representation of specified ``obj`` in file ``destination``,
        (either a file descriptor or a filename).
        """
        return self.blind_dump(pickle, obj, destination, **opts)

    def json_dump(self, obj, destination, **opts):
        """
        Dump a json representation of specified ``obj`` in file ``destination``,
        (either a file descriptor or a filename).
        """
        return self.blind_dump(json, obj, destination, **opts)

    def blind_load(self, source, gateway=None):
        """
        Use ``gateway`` for a blind load the representation stored in file ``source``,
        (either a file descriptor or a filename).
        """
        if hasattr(source, 'read'):
            obj = gateway.load(source)
        else:
            with io.open(self.path.expanduser(source), 'rb') as fd:
                obj = gateway.load(fd)
        return obj

    def pickle_load(self, source):
        """
        Load from a pickled representation stored in file ``source``,
        (either a file descriptor or a filename).
        """
        return self.blind_load(source, gateway=pickle)

    def json_load(self, source):
        """
        Load from a json representation stored in file ``source``,
        (either a file descriptor or a filename).
        """
        return self.blind_load(source, gateway=json)

    def pickle_clone(self, obj):
        """Clone an object through pickling / unpickling."""
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
        """Activate the signal catching."""
        self._sighandler.activate()

    def signal_intercept_off(self):
        """Deactivate the signal catching."""
        self._sighandler.deactivate()

    _LDD_REGEX = re.compile(r'^\s*([^\s]+)\s+=>\s*([^\s]+)\s+\(0x.+\)$')

    def ldd(self, filename):
        """Call ldd on a file.

        Return the mapping between the library name and its physical path
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


class Python26(object):
    """Old fashion features before Python 2.7."""

    def import_module(self, modname):
        """Import the module named ``modname`` with :mod:`imp` package."""
        import imp
        path = None
        buildname = ''
        for mod in modname.split('.'):
            mfile, mpath, minfo = imp.find_module(mod, path)
            path = [mpath]
            buildname = buildname + mod
            imp.load_module(buildname, mfile, mpath, minfo)
            buildname += '.'


class Python27(object):
    """Python features starting at version 2.7."""

    def import_module(self, modname):
        """Import the module named ``modname`` with :mod:`importlib` package."""
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
        """Import the function named ``funcname`` qualified by a proper module name package."""
        thisfunc = None
        if '.' in funcname:
            thismod = self.import_module('.'.join(funcname.split('.')[:-1]))
            if thismod:
                thisfunc = getattr(thismod, funcname.split('.')[-1], None)
        else:
            logger.error('Bad function path name <%s>' % funcname)
        return thisfunc


class Garbage(OSExtended, Python26):
    """
    Default system class for weird systems.
    Hopefully an extended system will be loaded later on.
    """

    _footprint = dict(
        info = 'Garbage base system',
        attr = dict(
            sysname = dict(
                outcast = [ 'Linux', 'Darwin' ]
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
    """Default system class for most linux based systems."""

    _abstract = True
    _footprint = dict(
        info = 'Linux base system',
        attr = dict(
            sysname = dict(
                values = ['Linux']
            )
        )
    )

    def __init__(self, *args, **kw):
        """
        Before going through parent initialisation, pickle this attributes:
          * psopts - as default option for the ps command (default: ``-w -f -a``).
        """
        logger.debug('Linux system init %s', self.__class__)
        self._psopts = kw.pop('psopts', ['-w', '-f', '-a'])
        super(Linux, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'linux'


class Linux26(Linux, Python26):
    """Specific Linux system with python version < 2.7"""

    _footprint = dict(
        info = 'Linux base system with pretty old python version',
        attr = dict(
            python = dict(
                values = [ '2.6.4', '2.6.5', '2.6.6' ]
            )
        )
    )


class Linux27(Linux, Python27):
    """Specific Linux system with python version >= 2.7"""

    _footprint = dict(
        info = 'Linux base system with pretty new python version',
        attr = dict(
            python = dict(
                values = ['2.7.' + str(x) for x in range(3, 15)]
            )
        )
    )


class LinuxDebug(Linux27):
    """Special system class for crude debugging on linux based systems."""

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


class Macosx(Linux, Python27):
    """Mac under MacOSX."""

    _footprint = dict(
        info = 'Apple Mac computer under Macosx',
        attr = dict(
            sysname = dict(
                values = ['Darwin']
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    @property
    def default_syslog(self):
        """address to use in logging.handler.SysLogHandler()"""
        return '/var/run/syslog'

    def ftp(self, hostname, logname=None):
        return super(Macosx, self).ftp(hostname, logname='lamboleyp')
