#!/bin/env python
# -*- coding: utf-8 -*-

r"""
This package handles system interfaces objects that are in charge of
system interaction. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, os, shutil, sys, io, filecmp, time
import glob
import subprocess

from vortex.autolog import logdefault as logger
from vortex.tools.env import Environment
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface
from vortex.tools.net import StdFtp


unamekeys = ('sysname', 'nodename', 'release', 'version', 'machine')
uname = dict(zip(unamekeys, os.uname()))


class System(BFootprint):
    """
    Root class for any :class:`System` subclasses.
    """

    _footprint = dict(
        info = 'Default information system',
        attr = dict(
            hostname = dict(
                optional = True,
                default = uname['nodename'],
                alias = ('nodename',)
            ),
            sysname = dict(
                optional = True,
                default = uname['sysname'],
            ),
            arch = dict(
                optional = True,
                default = uname['machine'],
                alias = ('machine',)
            ),
            release = dict(
                optional = True,
                default = uname['release']
            ),
            version = dict(
                optional = True,
                default = uname['version']
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract System init %s', self.__class__)
        if 'os' in kw:
            self._osmod = kw['os']
            del kw['os']
        if 'sh' in kw:
            self._shmod = kw['sh']
            del kw['sh']
        for flag in ( 'trace', 'output' ):
            self.__dict__[flag] = kw.setdefault(flag, True)
            del kw[flag]
        super(System, self).__init__(*args, **kw)

    def __getattr__(self, key):
        if key in self._os.__dict__:
            return self._os.__dict__[key]
        elif key in self._sh.__dict__:
            return self._sh.__dict__[key]
        else:
            raise AttributeError('method ' + key + ' not found')

    @classmethod
    def realkind(cls):
        return 'system'

    @property
    def _os(self):
        return self.__dict__.get('_osmod', os)

    @property
    def _sh(self):
        return self.__dict__.get('_shmod', shutil)

    @property
    def pwd(self):
        """Current working directory."""
        return self._os.getcwd()

    def cd(self, pathtogo):
        """Change directory to ``pathtogo``."""
        return self._os.chdir(pathtogo)

    def ffind(self, *args):
        """Récursive file find. Arguments are starting paths."""
        if not args:
            args = ['*']
        files = []
        for pathtogo in self.glob(*args):
            if self.path.isfile(pathtogo):
                files.append(pathtogo)
            else:
                for root, u_dirs, filenames in self._os.walk(pathtogo):
                    files.extend(map(lambda f: self.path.join(root, f), filenames))
        return sorted(files)

    @property
    def env(self):
        """Returns the current active environment."""
        return Environment.current()

    def echo(self, args):
        """Joined args are echoed."""
        print '>>>', ' '.join(args)

    def title(self, text='', tchar='=', autolen=76):
        """Formated title output."""
        if autolen:
            nbc = autolen
        else:
            nbc = len(text)
        print "\n", tchar * ( nbc + 4 )
        if text:
            print '{0:s} {1:^{size}s} {0:s}'.format(tchar, text.title(), size=nbc)
            print tchar * ( nbc + 4 )
        print "\n"

    def subtitle(self, text='', tchar='-', autolen=76):
        """Formated subtitle output."""
        if autolen:
            nbc = autolen
        else:
            nbc = len(text)
        print tchar * ( nbc + 4 )
        if text:
            print '# {0:{size}s} #'.format(text.title(), size=nbc)
            print tchar * ( nbc + 4 )

    def xperm(self, filename):
        """Return either a file exists and is executable or not."""
        if os.path.exists(filename):
            return bool(os.stat(filename).st_mode & 1)
        else:
            return False

    def which(self, command):
        """Clone of the unix command."""
        if command.startswith('/'):
            if self.xperm(command): return command
        else:
            for xpath in self.env.path.split(':'):
                fullcmd = os.path.join(xpath, command)
                if self.xperm(fullcmd): return fullcmd

    def touch(self, filename):
        """Clone of the unix command."""
        fh = file(filename, 'a')
        rc = True
        try:
            os.utime(filename, None)
        except:
            rc = False
        finally:
            fh.close()
        return rc

    def remove(self, filename):
        """Unlink the specified `filename` object."""
        if os.path.exists(filename):
            self.unlink(filename)
        return not os.path.exists(filename)

    def rm(self, filename):
        """Shortcut to remove."""
        return self.remove(filename)

    def ps(self, opts=[], search=None, pscmd=['ps']):
        pscmd.extend(self._psopts)
        pscmd.extend(opts)
        psall = subprocess.Popen(pscmd, stdout=subprocess.PIPE).communicate()[0].split('\n')
        if search:
            psall = filter(lambda x: re.search(search, x), psall)
        return map(lambda x: x.strip(), psall)

    def readonly(self, filename):
        """Set permissions of the `filename` object to read-only."""
        rc = None
        if os.path.exists(filename):
            rc = self.chmod(filename, 0444)
        return rc

    def sleep(self, nbsecs):
        """Clone of the unix command."""
        time.sleep(nbsecs)

    def spawn(self, args, ok=[0], shell=False, output=None):
        """Subprocess call of ``args``."""
        rc = False
        if output == None:
            output = self.output
        if self.trace:
            logger.info('System spawn < %s >', ' '.join(args))
        try:
            if output:
                # TODO new in 2.7
                rc = subprocess.check_output(args, shell=shell)
            else:
                rc = subprocess.check_call(args, shell=shell)
        except OSError as u_ose:
            logger.critical('Could not call %s', args)
            return False
        except subprocess.CalledProcessError as cpe:
            if cpe.returncode in ok:
                if output:
                    rc = cpe.output
            else:
                if output:
                    print cpe.output
                raise RuntimeError, "System %s spawned %s got %s" % (self, cpe.cmd, cpe.returncode)
        if output:
            rc = rc.rstrip("\n")
        else:
            rc = not bool(rc)
        return rc


class OSExtended(System):

    _abstract = True
    _footprint = dict(
        info = 'Extended base system'
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract System init %s', self.__class__)
        self._rmtreemin = kw.setdefault('rmtreemin', 3)
        del kw['rmtreemin']
        self._cmpaftercp = kw.setdefault('cmpaftercp', True)
        del kw['cmpaftercp']
        super(OSExtended, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'linux'

    def ftp(self, hostname, logname):
        """Returns an open ftp session on the specified target."""
        ftpbox = StdFtp(self, hostname)
        if ftpbox.fastlogin(logname):
            return ftpbox
        else:
            logger.warning('Could not login on %s as %s', hostname, logname)
            return None

    def filecocoon(self, destination):
        """Normalizes path name of the ``destination`` and creates this directory."""
        return self.mkdir(self.path.dirname(destination))

    def size(self, filepath):
        """Returns the actual size in bytes of the specified ``filepath``."""
        try:
            return self.stat(filepath).st_size
        except:
            return -1

    def mkdir(self, dirpath):
        """Normalizes path name and recursively creates this directory."""
        normdir = self.path.normpath(dirpath)
        if normdir and not self.path.isdir(normdir):
            logger.info('Cocooning directory %s', normdir)
            try:
                self.makedirs(normdir)
                return True
            except:
                return False
        else:
            return True

    def hybridcp(self, source, destination):
        """
        Copy the ``source`` file to a safe ``destination``.
        The return value is produced by a raw compare of the two files.
        """
        if type(source) == str:
            source = io.open(source, 'r')
            xsource = True
        else:
            xsource = False
        if type(destination) == str:
            self.filecocoon(destination)
            destination = io.open(destination, 'w')
            xdestination = True
        else:
            destination.seek(0)
            xdestination = False
        rc = self.copyfileobj(source, destination)
        if rc == None:
            rc = True
        if xsource:
            source.close()
        if xdestination:
            destination.close()
        return rc

    def cp(self, source, destination):
        """
        Copy the ``source`` file to a safe ``destination``.
        The return value is produced by a raw compare of the two files.
        """
        if type(source) != str or type(destination) != str:
            return self.hybridcp(source, destination)
        if self.filecocoon(destination):
            self.copyfile(source, destination)
            if self._cmpaftercp:
                return filecmp.cmp(source, destination)
            else:
                return bool(self.size(source) == self.size(destination))
        else:
            return False

    def glob(self, *args):
        """Glob file system entries according to ``args``. Returns a list."""
        entries = []
        for entry in args:
            if entry.startswith(':'):
                entries.append(entry[1:])
            else:
                entries.extend(glob.glob(entry))
        return entries

    def rmall(self, *args):
        """Unlink the specified `args` objects."""
        for pname in args:
            for filename in self.glob(pname):
                self.remove(filename)

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
                ( safedir, d ) = safepack
                rp = self.path.relpath(thispath, safedir)
                if not rp.startswith('..'):
                    if len(rp.split(os.sep)) < d:
                        logger.warning('Unsafe acces to %s relative to %s', thispath, safedir)
                        safe = False
        return safe

    def rmsafe(self, pathlist, safedirs):
        """Recursive unlinks the specified `args` objects if safe."""
        ok = True
        if type(pathlist) == str:
            pathlist = [ pathlist ]
        for pname in pathlist:
            for entry in filter(lambda x: self.safepath(x, safedirs), self.glob(pname)):
                if self.path.isdir(entry):
                    ok = ok and self.rmtree(entry)
                else:
                    ok = ok and self.remove(entry)
        return ok

    def _globcmd(self, cmd, args, ok=[0]):
        """Globbing files or directories as arguments before running ``cmd``."""
        cmd.extend([opt for opt in args if opt.startswith('-')])
        cmdlen = len(cmd)
        cmdargs = False
        for pname in [x for x in args if not x.startswith('-')]:
            cmdargs = True
            cmd.extend(self.glob(pname))
        if cmdargs and len(cmd) == cmdlen:
            return False
        else:
            return self.spawn(cmd, ok)

    def wc(self, *args):
        """Word count on globbed files."""
        return self._globcmd([ 'wc' ], args)

    def ls(self, *args):
        """Globbing and optional files or directories listing."""
        return self._globcmd([ 'ls' ], args)

    def dir(self, *args):
        """Proxy to ``ls('-l')``."""
        return self._globcmd([ 'ls', '-l' ], args)

    def cat(self, *args):
        """Globbing and optional files or directories listing."""
        return self._globcmd([ 'cat' ], args)

    def diff(self, *args):
        """Globbing and optional files or directories listing."""
        return self._globcmd([ 'diff' ], args, ok=[0, 1])

    def rmglob(self, *args):
        """Wrapper of the ``rm`` command through the globcmd."""
        return self._globcmd([ 'rm' ], args)

    def mv(self, source, destination):
        """Move the ``source`` file or directory."""
        return self.move(source, destination)

    def mvglob(self, *args):
        """Wrapper of the ``mv`` command through the globcmd."""
        return self._globcmd([ 'mv' ], args)

    def listdir(self, *args):
        if not args: args = ('.',)
        return self._os.listdir(args[0])

    def l(self, *args):
        rl = [x for x in args if not x.startswith('-')]
        if not rl: rl.append('*')
        return self.glob(*rl)

    def tar(self, *args):
        """Basic file archive command."""
        cmd = [ 'tar', args[0] ]
        cmd.extend(self.glob(args[1]))
        cmd.extend(args[2:])
        return self.spawn(cmd)


class Linux(OSExtended):
    """Default system class for most linux based systems."""

    _footprint = dict(
        info = 'Linux base system',
        attr = dict(
            sysname = dict(
                values = [ 'Linux', 'Darwin' ]
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Linux system init %s', self.__class__)
        self._psopts = kw.setdefault('psopts', ['-w', '-f', '-a'])
        del kw['psopts']
        super(Linux, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'linux'


class LinuxDebug(Linux):
    """Special system class for crude debugging on linux based systems."""

    _footprint = dict(
        info = 'Linux debug system',
        attr = dict(
            version = dict(
                optional = False,
                values = [ 'dbug', 'debug' ],
                remap = dict(
                    dbug = 'debug'
                )
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('LinuxDebug system init %s', self.__class__)
        super(LinuxDebug, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'linuxdebug'


class SuperUX(OSExtended):
    """NEC Operating System."""

    _footprint = dict(
        info = 'NEC operating system',
        attr = dict(
            sysname = dict(
                values = [ 'SUPER-UX' ]
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('SuperUX system init %s', self.__class__)
        self._psopts = kw.setdefault('psopts', ['-f'])
        del kw['psopts']
        super(SuperUX, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'super-ux'

    def cp(self, source, destination):
        """
        Copy the ``source`` file to a safe ``destination``.
        The return value is produced by a raw compare of the two files.
        """
        if type(source) != str or type(destination) != str:
            return self.hybridcp(source, destination)
        if self.filecocoon(destination):
            self.spawn(['cp', source, destination], output=False)
            return bool(self.size(source) == self.size(destination))
        else:
            logger.error('Could not create cocoon for %s', destination)
            return False


class SystemsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`System` items."""

    def __init__(self, **kw):
        logger.debug('Systems catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.system'),
            classes = [ System ],
            itementry = System.realkind()
        )
        cat.update(kw)
        super(SystemsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'systems'


cataloginterface(sys.modules.get(__name__), SystemsCatalog)
