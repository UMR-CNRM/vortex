#!/bin/env python
# -*- coding: utf-8 -*-

r"""
This package handles system interfaces objects that are in charge of
system interaction. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import logging, re, os, shutil, sys, io, filecmp, time
import glob
import subprocess

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
        logging.debug('Abstract System init %s', self.__class__)
        if 'os' in kw:
            self._osmod = kw['os']
            del kw['os']
        if 'sh' in kw:
            self._shmod = kw['sh']
            del kw['sh']
        self.trace = kw.setdefault('trace', True)
        del kw['trace']
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
                for root, dirs, filenames in self._os.walk(pathtogo):
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
        try:
            os.utime(filename, None)
        finally:
            fh.close()

    def sleep(self, nbsecs):
        """Clone of the unix command."""
        time.sleep(nbsecs)

    def spawn(self, args):
        """Subprocess call of ``args``."""
        rc = False
        if self.trace:
            logging.info('System spawn < %s >', ' '.join(args))
        try:
            rc = subprocess.call(args, shell=False)
        except OSError:
            logging.critical('Could not call %s', args)
        if rc:
            raise RuntimeError, "System %s spawned %s got %s" % (self, args, rc)
        return rc


class LinuxBase(System):

    _footprint = dict(
        info = 'Linux base system'
    )

    @classmethod
    def realkind(cls):
        return 'linux'

    def ftp(self, hostname, logname):
        """Returns an open ftp session on the specified target."""
        ftpbox = StdFtp(self, hostname)
        if ftpbox.fastlogin(logname):
            return ftpbox
        else:
            logging.warning('Could not login on %s as %s', hostname, logname)
            return None

    def filecocoon(self, destination):
        """Normalizes path name of the ``destination`` and creates this directory."""
        dir = self.path.normpath(self.path.dirname(destination))
        if dir and not self.path.isdir(dir):
            logging.info('Cocooning directory %s', dir)
            try:
                self.makedirs(dir)
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
            return filecmp.cmp(source, destination)
        else:
            return False

    def glob(self, *args):
        """Glob file system entries according to ``args``. Returns a list."""
        entries = []
        for entry in args:
            entries.extend(glob.glob(entry))
        return entries

    def remove(self, filename):
        """Unlink the specified `filename` object."""
        if os.path.exists(filename):
            self.unlink(filename)
        return not os.path.exists(filename)

    def rmall(self, *args):
        """Unlink the specified `args` objects."""
        for pname in args:
            for filename in self.glob(pname):
                self.remove(filename)

    def _globcmd(self, cmd, *args):
        """Globbing files or directories as arguments before running ``cmd``."""
        cmd.extend([opt for opt in args if opt.startswith('-')])
        for pname in filter(lambda x: not x.startswith('-'), args):
            cmd.extend(self.glob(pname))
        self.spawn(cmd)

    def ls(self, *args):
        """Globbing and optional files or directories listing."""
        self._globcmd([ 'ls' ], *args)

    def dir(self, *args):
        """Proxy to ``ls('-l')``."""
        self._globcmd([ 'ls', '-l' ], *args)

    def tar(self, *args):
        """Basic file archive command."""
        self._globcmd([ 'tar' ], *args)

    def mv(self, *args):
        """Wrapper of the ``mv`` command."""
        self._globcmd([ 'mv' ], *args)

    def cat(self, *args):
        """Wrapper of the ``cat`` command."""
        self._globcmd([ 'cat' ], *args)

    def ps(self, opts='-wwfa', search=None):
        psall = subprocess.Popen(['ps', opts], stdout=subprocess.PIPE).communicate()[0].split('\n')
        if search:
            psall = filter(lambda x: re.search(search,x), psall)
        return psall

    def readonly(self, filename):
        """Set permissions of the `filename` object to read-only."""
        rc = None
        if os.path.exists(filename):
            rc = self.chmod(filename, 0444)
        return rc


class SystemsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`System` items."""

    def __init__(self, **kw):
        logging.debug('Systems catalog init %s', self)
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
