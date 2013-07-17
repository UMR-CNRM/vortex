#!/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles system interfaces objects that are in charge of
system interaction. The associated modules defines the catalog
factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, os, platform, shutil, sys, io, filecmp, datetime, time
import glob
import tarfile
import subprocess

from vortex.autolog import logdefault as logger
from vortex.tools.env import Environment
from vortex.syntax import BFootprint, priorities
from vortex.utilities.catalogs import ClassesCollector, cataloginterface
from vortex.tools.net import StdFtp


class System(BFootprint):
    """
    Root class for any :class:`System` subclasses.
    """

    _footprint = dict(
        info = 'Default information system',
        attr = dict(
            hostname = dict(
                optional = True,
                default = platform.node(),
                alias = ('nodename',)
            ),
            sysname = dict(
                optional = True,
                default = platform.system(),
            ),
            arch = dict(
                optional = True,
                default = platform.machine(),
                alias = ('machine',)
            ),
            release = dict(
                optional = True,
                default = platform.release()
            ),
            version = dict(
                optional = True,
                default = platform.version()
            ),
            python = dict(
                optional = True,
                default = platform.python_version()
            )
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
        for flag in ( 'trace', ):
            self.__dict__[flag] = kw.setdefault(flag, False)
            del kw[flag]
        for flag in ( 'output', ):
            self.__dict__[flag] = kw.setdefault(flag, True)
            del kw[flag]
        super(System, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'system'

    def __getattr__(self, key):
        if key in self._os.__dict__:
            return self._os.__dict__[key]
        elif key in self._sh.__dict__:
            return self._sh.__dict__[key]
        else:
            raise AttributeError('method ' + key + ' not found')

    @property
    def _os(self):
        return self.__dict__.get('_osmod', os)

    @property
    def _sh(self):
        return self.__dict__.get('_shmod', shutil)

    def stderr(self, args):
        """Write a formatted message to standard error."""
        if self.trace:
            sys.stderr.write(
                "+ [{0:s}] {1:s}\n".format(
                    datetime.datetime.now().strftime('%Y/%m/%d-%H:%M:%S'),
                    ' '.join(args)
                )
            )

    def pwd(self, output=None):
        """Current working directory."""
        if output == None:
            output = self.output
        self.stderr(['pwd'])
        realpwd = self._os.getcwd()
        if output:
            return realpwd
        else:
            print realpwd
            return True

    def cd(self, pathtogo):
        """Change directory to ``pathtogo``."""
        self.stderr(['cd', pathtogo])
        try:
            self._os.chdir(pathtogo)
            return True
        except OSError:
            return False
        except:
            raise

    def ffind(self, *args):
        """Recursive file find. Arguments are starting paths."""
        if not args:
            args = ['*']
        files = []
        self.stderr(['ffind'] + list(args))
        for pathtogo in self.glob(*args):
            if self.path.isfile(pathtogo):
                files.append(pathtogo)
            else:
                for root, u_dirs, filenames in self._os.walk(pathtogo):
                    files.extend([ self.path.join(root, f) for f in filenames ])
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
        self.stderr(['which', command])
        if command.startswith('/'):
            if self.xperm(command): return command
        else:
            for xpath in self.env.path.split(':'):
                fullcmd = os.path.join(xpath, command)
                if self.xperm(fullcmd): return fullcmd

    def touch(self, filename):
        """Clone of the unix command."""
        self.stderr(['touch', filename])
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
        self.stderr(['remove', filename])
        if os.path.exists(filename):
            self.unlink(filename)
        return not os.path.exists(filename)

    def rm(self, filename):
        """Shortcut to remove."""
        return self.remove(filename)

    def ps(self, opts=[], search=None, pscmd=None):
        if not pscmd:
            pscmd = ['ps']
        pscmd.extend(self._psopts)
        pscmd.extend(opts)
        self.stderr(pscmd)
        psall = subprocess.Popen(pscmd, stdout=subprocess.PIPE).communicate()[0].split('\n')
        if search:
            psall = filter(lambda x: re.search(search, x), psall)
        return [ x.strip() for x in psall ]

    def readonly(self, inodename):
        """Set permissions of the `filename` object to read-only."""
        self.stderr(['readonly', nbsecs])
        rc = None
        if os.path.exists(inodename):
            if os.path.isdir(inodename):
                rc = self.chmod(inodename, 0555)
            else:
                rc = self.chmod(inodename, 0444)
        return rc

    def sleep(self, nbsecs):
        """Clone of the unix command."""
        self.stderr(['sleep', nbsecs])
        time.sleep(nbsecs)

    def vortex_modules(self, only='.'):
        """Return a filtered list of modules in the vortex package."""
        g = self.env.glove
        mroot = g.siteroot + '/src'
        mfiles = [ re.sub('^' + mroot + '/', '', x) for x in self.ffind(mroot) ]
        return [
            re.sub('(?:\/__init__)?\.py$', '', x).replace('/', '.')
            for x in mfiles if ( re.search(only, x, re.IGNORECASE) and x.endswith('.py') )
        ]

    def systems_reload(self):
        """Load extra systems modules not yet loaded."""
        extras = list()
        for modname in self.vortex_modules('systems'):
            if modname not in sys.modules:
                self.import_module(modname)
                extras.append(modname)
        return extras

    def spawn(self, args, ok=[0], shell=False, output=None):
        """Subprocess call of ``args``."""
        rc = False
        if output == None:
            output = self.output
        self.stderr(args)
        p = None
        try:
            if output:
                cmdout, cmderr = subprocess.PIPE, subprocess.PIPE
            else:
                cmdout, cmderr = None, None
            p = subprocess.Popen(args, stdout=cmdout, stderr=cmderr, shell=shell)
            p.wait()
        except ValueError as perr:
            logger.critical('Weird arguments to Popen ( %s, stdout=%s, stderr=%s, shell=%s )' %args, cmdout, cmderr, shell)
            logger.critical('System returns %s', str(perr))
            return False
        except OSError as perr:
            logger.critical('Could not call %s', args)
            logger.critical('System returns %s', str(perr))
            return False
        except Exception as perr:
            logger.critical('System returns %s', str(perr))
            raise RuntimeError, "System %s spawned %s got [%s]" % (self, args, perr.returncode)
        else:
            if p.returncode in ok:
                if output:
                    rc = [ x.rstrip("\n") for x in p.stdout ]
                    p.stdout.close()
                else:
                    rc = not bool(p.returncode)
            else:
                logger.warning('Bad return code [%d] for %s', p.returncode, args)
                if output:
                    for xerr in p.stderr:
                        sys.stderr.write(xerr)
                return False
        finally:
            if output and p:
                p.stdout.close()
                p.stderr.close()

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
        self.stderr(['size', filepath])
        try:
            return self.stat(filepath).st_size
        except:
            return -1

    def mkdir(self, dirpath):
        """Normalizes path name and recursively creates this directory."""
        normdir = self.path.normpath(dirpath)
        if normdir and not self.path.isdir(normdir):
            logger.debug('Cocooning directory %s', normdir)
            self.stderr(['mkdir', normdir])
            try:
                self.makedirs(normdir)
                return True
            except OSError:
                return False
        else:
            return True

    def rawcp(self, source, destination):
        """Internal basic cp command used by :meth:`cp` or :meth:`smartcp`."""
        self.stderr(['rawcp', source, destination])
        self.copyfile(source, destination)
        if self._cmpaftercp:
            return filecmp.cmp(source, destination)
        else:
            return bool(self.size(source) == self.size(destination))

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
            if self.filecocoon(destination):
                if self.remove(destination):
                    destination = io.open(destination, 'w')
                    xdestination = True
                else:
                    logger.error('Could not remove destination before copy %s', destination)
                    return False
            else:
                logger.error('Could not create a cocoon for file %s', destination)
                return False
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

    def smartcp(self, source, destination):
        """
        Hard link the ``source`` file to a safe ``destination`` if possible.
        Otherwise, let the standard copy do the job.
        """
        if type(source) != str or type(destination) != str:
            return self.hybridcp(source, destination)
        if not self.path.exists(source):
            logger.warning('Source does not exist: %s', source)
            return False
        if self.filecocoon(destination):
            if self.remove(destination):
                st1 = self.stat(source)
                st2 = self.stat(self.path.dirname(self.path.realpath(destination)))
                if st1 and st2:
                    if st1.st_dev == st2.st_dev and not self.path.islink(source):
                        self.link(source, destination)
                        self.readonly(destination)
                        return self.path.samefile(source, destination)
                    else:
                        rc = self.rawcp(source, destination)
                        if rc:
                            self.readonly(destination)
                        return rc
                else:
                    logger.error('Could not stat either source or destination (%s/%s)', st1, st2)
                    return False
            else:
                logger.error('Could not remove destination before copy %s', destination)
                return False
        else:
            logger.error('Could not create a cocoon for file %s', destination)
            return False

    def cp(self, source, destination):
        """
        Copy the ``source`` file to a safe ``destination``.
        The return value is produced by a raw compare of the two files.
        """
        self.stderr(['cp', source, destination])
        if type(source) != str or type(destination) != str:
            return self.hybridcp(source, destination)
        if self.filecocoon(destination):
            if self.remove(destination):
                return self.rawcp(source, destination)
            else:
                logger.error('Could not remove destination before copy %s', destination)
                return False
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
                entries.extend(glob.glob(entry))
        return entries

    def rmall(self, *args):
        """Unlink the specified `args` objects."""
        rc = True
        for pname in args:
            for filename in self.glob(pname):
                rc = self.remove(filename) and rc

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
                    ok = self.rmtree(entry) and ok
                else:
                    ok = self.remove(entry) and ok
        return ok

    def _globcmd(self, cmd, args, **kw):
        """Globbing files or directories as arguments before running ``cmd``."""
        cmd.extend([opt for opt in args if opt.startswith('-')])
        cmdlen = len(cmd)
        cmdargs = False
        globtries = [x for x in args if not x.startswith('-')]
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
        return self._globcmd([ 'wc' ], args, **kw)

    def ls(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        return self._globcmd([ 'ls' ], args, **kw)

    def dir(self, *args, **kw):
        """Proxy to ``ls('-l')``."""
        return self._globcmd([ 'ls', '-l' ], args, **kw)

    def cat(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        return self._globcmd([ 'cat' ], args, **kw)

    def diff(self, *args, **kw):
        """Globbing and optional files or directories listing."""
        kw.setdefault('ok', [0, 1])
        return self._globcmd([ 'diff' ], args, **kw)

    def rmglob(self, *args, **kw):
        """Wrapper of the ``rm`` command through the globcmd."""
        return self._globcmd([ 'rm' ], args, **kw)

    def mv(self, source, destination):
        """Move the ``source`` file or directory."""
        try:
            self.move(source, destination)
        except:
            raise
        else:
            return True

    def mvglob(self, *args):
        """Wrapper of the ``mv`` command through the globcmd."""
        return self._globcmd([ 'mv' ], args)

    def listdir(self, *args):
        if not args: args = ('.',)
        self.stderr(['listdir'] + list(args))
        return self._os.listdir(args[0])

    def l(self, *args):
        rl = [x for x in args if not x.startswith('-')]
        if not rl: rl.append('*')
        return self.glob(*rl)

    def is_tarfile(self, filename):
        """Return a boolean according to the tar status of the ``filename``."""
        return tarfile.is_tarfile(filename)

    def _tarcx(self, *args, **kw):
        """Raw file archive command."""
        cmd = [ 'tar', kw.setdefault('cx', 'c') ]
        del kw['cx']
        cmd.extend(self.glob(args[0]))
        optforce = 'opts' in kw
        zopt = set(cmd[1]) | set(kw.setdefault('opts', 'f'))
        del kw['opts']
        if not optforce:
            if kw.setdefault('verbose', True):
                zopt.add('v')
            else:
                zopt.discard('v')
            del kw['verbose']
            if cmd[-1].endswith('gz'):
                zopt.add('z')
            else:
                zopt.discard('z')
        cmd[1] = ''.join(zopt)
        cmd.extend(args[1:])
        return self.spawn(cmd, **kw)

    def tar(self, *args, **kw):
        """Create a file archive (always c-something)'"""
        kw['cx'] = 'c'
        self._tarcx(*args, **kw)

    def untar(self, *args, **kw):
        """Unpack a file archive (always x-something)'"""
        kw['cx'] = 'x'
        self._tarcx(*args, **kw)


class Python26(object):
    """Old fashion features before Python 2.7."""

    def import_module(self, modname):
        import imp
        path = None
        buildname = ''
        for mod in modname.split('.'):
            mfile, mpath, minfo = imp.find_module(mod, path)
            path = [ mpath ]
            buildname = buildname + mod
            imp.load_module(buildname, mfile, mpath, minfo)
            buildname = buildname + '.'


class Python27(object):
    """Python features starting at version 2.7."""

    def import_module(self, modname):
        try:
            import importlib
        except ImportError:
            logger.critical('No way to get importlob in python 2.7 ... something really weird !')
            raise
        except:
            logger.critical('Unexpected error: %s', sys.exc_info()[0])
            raise
        else:
            importlib.import_module(modname)


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
            level = priorities.top.DEFAULT
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Garbage system init %s', self.__class__)
        super(Garbage, self).__init__(*args, **kw)


class Linux(OSExtended):
    """Default system class for most linux based systems."""

    _abstract = True
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
                values = [ '2.7.' + str(x) for x in range(2,7) ]
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

    @property
    def realkind(self):
        return 'linuxdebug'


class SystemsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`System` items."""

    def __init__(self, **kw):
        logger.debug('Systems catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.system'),
            classes = [ System ],
            itementry = 'system'
        )
        cat.update(kw)
        super(SystemsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'systems'


cataloginterface(sys.modules.get(__name__), SystemsCatalog)
