#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time
import fcntl
import io
import json
import resource
import signal
import traceback
import subprocess
import multiprocessing

from ast          import literal_eval
from datetime     import datetime
from signal       import SIGTERM
from ConfigParser import SafeConfigParser

import footprints

from . import pools

#: No automatic export
__all__ = []


class GentleTalk(object):
    """An alternative to the logging interface that can be exchanged between processes."""

    _levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

    DEBUG    = '\033[94m'
    INFO     = '\033[0m'
    WARNING  = '\033[93m'
    ERROR    = '\033[95m'
    CRITICAL = '\033[91m'
    ENDC     = '\033[0m'
    BOLD     = '\033[1m'
    HEADER   = '\033[95m'
    OKBLUE   = '\033[94m'
    OKGREEN  = '\033[92m'

    def __init__(self, datefmt='%Y/%d/%m-%H:%M:%S', loglevel=1, taskno=0):
        self._datefmt  = datefmt
        self._taskno   = int(taskno)
        self.loglevel  = loglevel

    def clone(self, taskno):
        """Clone the actual logger with a different task number."""
        return self.__class__(loglevel=self.loglevel, taskno=taskno)

    @property
    def levels(self):
        return self.__class__._levels

    @property
    def datefmt(self):
        return self._datefmt

    @property
    def taskno(self):
        return self._taskno

    def _get_loglevel(self):
        return self._loglevel

    def _set_loglevel(self, value):
        try:
            value = int(value)
        except ValueError:
            try:
                value = self.levels.index(value.upper())
            except StandardError:
                value = -1
        if 0 <= value <= len(self.levels):
            self._loglevel = value
        return self._loglevel

    loglevel = property(_get_loglevel, _set_loglevel)

    @property
    def levelname(self):
        return self.levels[self._loglevel]

    def _msgfmt(self, level, msg, args, kw):
        """Formatting log message as `msg <key:value> ...` string."""
        if self.levels.index(level.upper()) >= self.loglevel:
            msg = str(msg) + ' ' + ' '.join([
                '<' + k + ':' + str(v) + '>' for k, v in kw.items()
            ])
            thisprocess = multiprocessing.current_process()
            mutex = multiprocessing.Lock()
            mutex.acquire()
            print '{color}# [{0:s}][P{1:06d}][T{2:06d}][{3:13s}:{4:>8s}] {5:s}{endcolor}'.format(
                datetime.now().strftime(self.datefmt),
                thisprocess.pid,
                self.taskno,
                thisprocess.name,
                level.upper(),
                msg,
                color = getattr(self, level.upper()),
                endcolor = self.ENDC
            )
            mutex.release()

    def debug(self, msg, *args, **kw):
        return self._msgfmt('debug', msg, args, kw)

    def info(self, msg, *args, **kw):
        return self._msgfmt('info', msg, args, kw)

    def warning(self, msg, *args, **kw):
        return self._msgfmt('warning', msg, args, kw)

    def error(self, msg, *args, **kw):
        return self._msgfmt('error', msg, args, kw)

    def critical(self, msg, *args, **kw):
        return self._msgfmt('critical', msg, args, kw)


class ExitHandler(object):
    """Context manager for SIGTERM and Co. signals."""

    def __init__(self, daemon, on_exit=None, on_stack=False):
        self._on_stack = on_stack
        self._daemon   = daemon
        try:
            on_exit[0]
        except TypeError:
            on_exit = (on_exit,)
        self._on_exit  = tuple(on_exit)

    @property
    def on_stack(self):
        return self._on_stack

    @property
    def on_exit(self):
        return self._on_exit

    @property
    def daemon(self):
        return self._daemon

    @staticmethod
    def sigterm_handler(signum, frame):
        """Proper system exit."""
        sys.exit(0)

    def __enter__(self):
        old_handler = signal.signal(signal.SIGTERM, self.sigterm_handler)
        if (old_handler != signal.SIG_DFL) and (old_handler != self.sigterm_handler):
            if not self.on_stack:
                raise RuntimeError('Handler already registered for SIGTERM: [%r]' % old_handler)
            def handler(signum, frame):
                try:
                    self.sigterm_handler(signum, frame)
                finally:
                    old_handler(signum, frame)
            signal.signal(signal.SIGTERM, handler)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Be sure to call all registred callbacks at exit time."""
        self.daemon.info('Context exit ' + repr(self.daemon))
        self.daemon.info('Context exit ' + repr(exc_type))
        if exc_value.message:
            self.daemon.critical('Context exit', error=exc_value)
            print "\n", '-' * 80
            print exc_value.message
            print '-' * 80, "\n"
            print "\n".join(traceback.format_tb(exc_traceback))
            print '-' * 80, "\n"
        else:
            self.daemon.info('Context exit', value=exc_value)
        for callback in [x for x in self.on_exit if x is not None]:
            self.daemon.info('Context callback ' + repr(callback))
            callback()
        return True


class PidFile(object):
    """
    Class in charge of pid handling in a simple file.
    """

    def __init__(self, tag='default', filename=None, procname='python'):
        if filename is None:
            filename = '/tmp/daemon-' + os.getlogin() + '-' + tag
        if not filename.endswith('.pid'):
            filename += '.pid'
        self._filename = os.path.realpath(filename)
        self._procname = procname
        self.reset()

    def reset(self):
        try:
            self._fd = os.open(self._filename, os.O_CREAT | os.O_RDWR)
        except IOError as iotrouble:
            sys.exit('Failed to open pidfile: %s' % str(iotrouble))
        assert not fcntl.flock(self._fd, fcntl.LOCK_EX)

    @property
    def fd(self):
        return self._fd

    @property
    def filename(self):
        return self._filename

    @property
    def procname(self):
        return self._procname

    def unlock(self):
        assert not fcntl.flock(self.fd, fcntl.LOCK_UN)

    def write(self, pid=None):
        if pid is None:
            pid = os.getpid()
        os.ftruncate(self.fd, 0)
        os.write(self.fd, "%d\n" % int(pid))
        os.fsync(self.fd)

    def delfile(self):
        """Remove actual pid filename."""
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def kill(self, retry=10):
        pid = int(os.read(self.fd, 4096))
        os.lseek(self.fd, 0, os.SEEK_SET)

        try:
            while retry > 0:
                os.kill(pid, SIGTERM)
                print 'Sending SIGTERM to', pid, '...'
                time.sleep(0.2)
                retry -= 1
        except OSError as err:
            err = str(err)
            if err.find('No such process') > 0:
                self.delfile()
            else:
                return str(err)

        if self.is_running():
            return 'Failed to kill %d' % pid

    def is_running(self):
        contents = os.read(self.fd, 4096)
        os.lseek(self.fd, 0, os.SEEK_SET)

        if not contents:
            return False

        p = subprocess.Popen(
            ['ps', '-o', 'comm', '-p', str(int(contents))],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
        if stdout == "COMM\n":
            return False

        if self.procname in stdout[stdout.find("\n")+1:]:
            return True

        return False


class BaseDaemon(object):
    """
    A generic daemon class.
    Thanks to Sander Marechal : http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    With some modifications and PidFile creation.

    Usage: subclass the BaseDaemon class and override the run() method
    """
    def __init__(self, tag='test', pidfile=None, loglevel=1, inifile=None, redirect=None):
        self._tag        = tag
        self._pidfile    = PidFile(tag=tag, filename=pidfile or tag)
        self._tmpdir     = os.path.join(os.environ['HOME'], 'tmp')
        self._rundir     = os.getcwd()
        self._logger     = None
        self._loglevel   = loglevel
        self._stdin      = os.devnull
        self._redirect   = os.path.realpath(redirect or tag + '.log')
        self._daemonized = False
        self._inifile    = self._tag if inifile is None else inifile
        if not self._inifile.endswith('.ini'):
            self._inifile += '.ini'

    @property
    def tag(self):
        return self._tag

    @property
    def daemonized(self):
        return self._daemonized

    @property
    def stdin(self):
        return self._stdin

    @property
    def stdout(self):
        return self._redirect

    @property
    def stderr(self):
        return self._redirect

    @property
    def pidfile(self):
        return self._pidfile

    @property
    def tmpdir(self):
        return self._tmpdir

    @property
    def rundir(self):
        return self._rundir

    @property
    def loglevel(self):
        return self._loglevel

    @property
    def logger(self):
        if self._logger is None:
            self._logger = GentleTalk()
        return self._logger

    def debug(self, msg, **kw):
        return self.logger.debug(msg, **kw)

    def info(self, msg, **kw):
        return self.logger.info(msg, **kw)

    def warning(self, msg, **kw):
        return self.logger.warning(msg, **kw)

    def error(self, msg, **kw):
        return self.logger.error(msg, **kw)

    def critical(self, msg, **kw):
        return self.logger.critical(msg, **kw)

    @property
    def inifile(self):
        return self._inifile

    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        self._daemonized = True

    def ioremap(self):
        """Remap standard io file descriptors."""

        # close all the possible file descriptors opened
        if self.daemonized:
            maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
            if maxfd == resource.RLIM_INFINITY:
                maxfd = 1024
            for fd in range(3, maxfd):
                try:
                    os.close(fd)
                except OSError:   # ERROR, fd wasn't open to begin with (ignored)
                    pass

        # remap std 0, 1 and 2
        if self.daemonized:
            sys.stdin.close()
            sys.stdin = open(self.stdin, 'r')
        if self.stdout is not None:
            sys.stdout.flush()
            sys.stderr.flush()
            if self.stdout and os.path.exists(self.stdout):
                os.rename(self.stdout, self.stdout + '.' + pools.timestamp())
            stdnew = open(self.stdout, 'a+', 1)
            os.dup2(stdnew.fileno(), sys.stdout.fileno())
            os.dup2(stdnew.fileno(), sys.stderr.fileno())

    def header(self):
        """Introduction to logging file..."""
        os.chdir(self.rundir)
        self.info('Daemon', started=datetime.now())
        self.info('Daemon', tag=self.tag)
        self.info('Daemon', kind=self.__class__.__name__)
        self.info('Daemon', module=self.__module__)
        self.info('Process', pid=os.getpid())
        self.info('Process', pidfile=self.pidfile.filename)
        self.info('Process', rundir=self.rundir)
        self.info('Process', tmpdir=self.tmpdir)

    def bye(self):
        """Nice exit."""
        self.pidfile.delfile()
        self.info('Bye folks...')

    def exit_callbacks(self):
        """Return a list of callbacks to be launch before daemon exit."""
        return (self.bye,)

    def start(self, mkdaemon=True):
        """Start the daemon."""

        # check for a pidfile to see if the daemon already runs
        if self.pidfile.is_running():
            self.pidfile.unlock()
            sys.exit('Daemon already running.')

        # start the daemon
        print 'Starting daemon...'
        if mkdaemon:
            self.daemonize()

        # write pidfile
        self.pidfile.write()
        self.pidfile.unlock()

        # gather std descriptors
        self.ioremap()

        # let's be a bit talkative
        self.header()
        if sys.path[0] == '':
            sys.path.pop(0)
        sys.path.insert(0, self.rundir)

        # at least, do something...
        with ExitHandler(self, on_exit=self.exit_callbacks()):
            self.setup()
            self.run()

    def stop(self):
        """Stop the daemon."""

        # check if a daemon is actually running
        if not self.pidfile.is_running():
            self.pidfile.unlock()
            print 'Daemon not running.'
            return

        # try to nicelly kill the daemon process
        error = self.pidfile.kill()
        if error:
            self.pidfile.unlock()
            sys.exit(error)


    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.pidfile.reset()
        self.start()

    def setup(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized by start() or restart() and before run().
        """
        pass

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized by start() or restart() after setup().
        """
        pass


class HouseKeeping(object):
    """A wrapper for all internal config callbacks."""

    def internal_reload(self, ask):
        """Proxy to a setup rerun."""
        if ask.data is None:
            self.error('Reload undefined')
            return False
        else:
            self.multi_stop()
            if 'config' in ask.data:
                self.warning('Rerun setup config')
                self.config = self.read_config(self.inifile)
            if 'mkpools' in ask.data:
                self.warning('Rerun setup mkpools')
                self.mkpools(clear=True)
            self.multi_start()
            return True

    def internal_level(self, ask):
        """Set a specific log level."""
        self.logger.loglevel = ask.data
        self.warning('Switch log', level=self.logger.levelname)
        return True

    def internal_sleep(self, ask):
        """Make a nap."""
        self.warning('Sleep', duration=ask.data)
        time.sleep(ask.data)
        return True

    def internal_show(self, ask=None, actualcfg=None, scope='global'):
        """Display on stdout the current configuration."""
        if actualcfg is None:
            actualcfg = self.config
        print "\n", '-' * 80
        print scope.upper(), 'CONFIGURATION DISPLAY'
        print '-' * 80
        for section, infos in sorted(actualcfg.items()):
            print "\n", ' *', section
            for k, v in sorted(infos.items()):
                print '   +', k.ljust(16), '=', v
        print "\n", '-' * 80, "\n"
        return True

    def internal_update(self, ask):
        """Update the current configuration and display it."""
        if ask.data is not None and isinstance(ask.data, dict):
            self.internal_show(actualcfg=ask.data, scope='update')
            footprints.util.dictmerge(self.config, ask.data)
            return True
        else:
            self.error('Not a valid update', data=type(ask.data))
            return False

    def internal_switch_pool(self, ask, status=False):
        """Update active parameters for pools."""
        for pool in [ x.lower() for x in footprints.util.mktuple(ask.data) ]:
            poolcfg = 'pool_' + pool
            if poolcfg in self.config:
                self.warning('Switch pool', active=status)
                self.config[poolcfg]['active'] = status
                thispool = pools.get(tag=pool)
                thispool.active = status
        return True

    def internal_active(self, ask):
        """Proxy to pool switch on."""
        return self.internal_switch_pool(ask, status=True)

    def internal_mute(self, ask):
        """Proxy to pool switch off."""
        return self.internal_switch_pool(ask, status=False)

    def internal_switch_action(self, ask, status=False):
        """Update active parameters for an action."""
        for action in [ x.lower() for x in footprints.util.mktuple(ask.data) ]:
            actioncfg = 'action_' + action
            if actioncfg not in self.config:
                self.config[actioncfg] = dict()
            self.warning('Switch action', active=status)
            self.config[actioncfg]['active'] = status
        return True

    def internal_seton(self, ask):
        """Proxy to action switch on."""
        return self.internal_switch_action(ask, status=True)

    def internal_setoff(self, ask):
        """Proxy to action switch off."""
        return self.internal_switch_action(ask, status=False)


class Jeeves(BaseDaemon, HouseKeeping):
    """Multiprocessed and modular daemon."""

    def read_config(self, filename):
        """Parse a configuration file and try to evaluate values as best as we can."""
        config = dict(driver=dict(pools=[]))
        if os.path.exists(self.inifile):
            self.absfile = os.path.abspath(self.inifile)
            self.info('Configuration', path=self.absfile)
            cfg = SafeConfigParser()
            cfg.read(self.absfile)
            self.info('Configuration', sections=','.join(cfg.sections()))
            for section in cfg.sections():
                if section not in config:
                    config[section] = dict()
                for k, v in cfg.items(section):
                    try:
                        v = literal_eval(v)
                    except (SyntaxError, ValueError):
                        if k.startswith('options') or ',' in v:
                            v = [ x for x in v.replace(' ', '').split(',') ]
                    config[section][k.lower()] = v
        else:
            self.error('No configuration', path=self.inifile)
        return config

    def mkpools(self, clear=False):
        """Create directories according to config file or default names."""
        if clear:
            pools.clear_all()
        for pool in self.config['driver'].get('pools', tuple()):
            poolcfg = 'pool_' + pool
            if poolcfg not in self.config:
                self.warning('No dedicated conf', pool=pool)
                self.config[poolcfg] = dict()
            thispool = pools.get(tag=pool, logger=self.logger, **self.config[poolcfg])
            if os.path.isdir(thispool.path):
                self.info('Mkdir skipped', pool=thispool.tag, path=thispool.path, size=len(thispool.contents))
            else:
                self.warning('Mkdir', pool=thispool.tag, path=thispool.path)
                os.mkdir(thispool.path, 0755)

    def setup(self):
        """
        Read any configuration file provided as tag.ini
        and create appropriate directories.
        """

        # read ini configuration file if any
        self.config = self.read_config(self.inifile)

        # check or create pool directories
        self.mkpools()

    def multi_start(self):
        """Start a pool of co-workers processes."""
        self.ptask = 0
        self.async = dict()
        self.procs = self.config['driver'].get('maxprocs', 4)
        maxtasks = self.config['driver'].get('maxtasks', 64)
        self.ppool = multiprocessing.Pool(self.procs, None, None, maxtasks)
        self.info('Start multiprocessing', procs=self.procs)
        for child in sorted(multiprocessing.active_children(), key=lambda x: x.pid):
            self.info('Coprocess', pid=child.pid, alive=child.is_alive(), name=child.name)
        return True

    def multi_stop(self, timeout=1):
        """Join all active coprocesses."""
        if self.procs:
            # at least, some multiproccessing setup had occured
            self.info('Terminate', procs=self.procs, remaining=len(self.async))

            # look at the remaining tasks
            for (pnum, syncinfo) in self.async.items():
                self.warning('Task not complete', pnum=pnum)
                try:
                    jpool, jfile, asyncr = syncinfo
                    pnum, prc, pvalue = asyncr.get(timeout=timeout)
                except multiprocessing.TimeoutError:
                    self.error('Timeout for task', pnum=pnum)
                except StandardError as trouble:
                    self.critical('Trouble in pool', pnum=pnum, error=trouble)
                else:
                    self.info('Return', pnum=pnum, rc=prc, result=pvalue)
                    self.migrate(pools.get(tag=jpool), jfile)
                finally:
                    del self.async[pnum]

            # try to clean the current active pool of processes
            try:
                self.ppool.close()
                self.ppool.terminate()
                self.ppool.join()
            except StandardError as trouble:
                self.critical('Multiprocessing stop', error=trouble)

        else:
            self.warning('Multi stop without start ?')

        return True

    def migrate(self, pool, item, target=None):
        """Proxy to pool migration service."""
        rc = None
        try:
            target = pool.migrate(item, target=target)
            rc = pools.get(tag=target)
        except OSError as trouble:
            self.error('Could not migrate', item=item, error=trouble)
        else:
            self.info('Migrate', item=item, target=rc.path)
        return rc

    def json_load(self, pool, item):
        """Load a json request file."""
        obj = None
        jsonfile = os.path.join(pool.path, item)
        try:
            with io.open(jsonfile, 'rb') as fd:
                obj = json.load(fd)
            obj = pools.Request(**obj)
        except StandardError:
            self.error('Could not load', path=jsonfile)
            self.migrate(pool, item, target='error')
        return obj

    def import_module(self, modname):
        """Import the module named ``modname`` with :mod:`importlib` package."""
        if modname not in sys.modules:
            try:
                import importlib
            except ImportError:
                self.critical('Import failed', module='importlib')
                raise
            except:
                self.critical('Unexpected', error=sys.exc_info()[0])
                raise
            else:
                try:
                    importlib.import_module(modname)
                except ImportError:
                    self.error('Could not import', module=modname)
        return sys.modules.get(modname)

    def async_callback(self, result):
        """Get result from async pool processing."""
        if result:
            pnum = None
            prc = None
            try:
                pnum, prc, pvalue = result
                if prc:
                    self.info('Return', pnum=pnum, result=pvalue)
                else:
                    self.error('Return', pnum=pnum, error=pvalue)
            except StandardError as trouble:
                self.critical('Callback', error=trouble, result=result)
            finally:
                if pnum is not None and pnum in self.async:
                    jpool, jfile, asyncr = self.async[pnum]
                    poolbase = pools.get(tag=jpool)
                    pooltarget = None
                    if prc:
                        try:
                            pooltarget = pvalue.get('rpool', None)
                        except StandardError:
                            pass
                    else:
                        pooltarget = 'error'
                    self.migrate(poolbase, jfile, target=pooltarget)
                    del self.async[pnum]
                else:
                    self.error('Unknown async process', pnum=pnum)
        else:
            self.error('Undefined result from async processing')

    def dispatch(self, func, ask, acfg, jpool, jfile):
        """Multiprocessing dispatching."""
        rc = False
        self.ptask += 1
        pnum = '{0:06d}'.format(self.ptask)
        opts = ask.opts.copy()
        for extra in [ x for x in acfg.get('options', tuple()) if x not in opts ]:
            opts[extra] = acfg.get(extra, None)
        try:
            self.async[pnum] = (
                jpool,
                jfile,
                self.ppool.apply_async(
                    func,
                    (pnum, ask, self.config.copy(), self.logger.clone(pnum)),
                    opts,
                    self.async_callback
                )
            )
        except StandardError as trouble:
            self.critical('Dispatch', error=trouble, action=ask.todo)
        else:
            rc = True
            self.info('Dispatch', pnum=pnum, action=ask.todo)
        return rc

    def process_request(self, pool, jfile):
        """Process a standard request."""
        rc = False
        dispatched = False
        ask = self.json_load(pool, jfile)
        if ask is not None:
            tp = self.migrate(pool, jfile)
            if tp is not None:
                rc = True
                rctarget = 'error'
                if ask.todo in self.config['driver'].get('actions', tuple()):
                    action = 'action_' + ask.todo
                    if action in self.config:
                        acfg = self.config[action]
                    else:
                        self.warning('Undefined', action=ask.todo)
                        acfg = dict(
                            dispatch = False,
                            module   = 'internal',
                            entry    = ask.todo,
                        )
                    if acfg.get('active', True):
                        thismod  = acfg.get('module', 'internal')
                        thisname = acfg.get('entry', ask.todo)
                        self.info('Processing',
                            action   = ask.todo,
                            function = thisname,
                            module   = thismod,
                        )
                        if thismod == 'internal':
                            thisfunc = getattr(self, 'internal_' + thisname, None)
                        else:
                            thismobj = self.import_module(thismod)
                            if thismobj:
                                thisfunc = getattr(thismobj, thisname, None)
                            else:
                                self.error('Import failed', module=acfg.get('module'))
                                thisfunc = None
                                rc = False
                        if thisfunc is None or not callable(thisfunc):
                            self.error('Not a function', entry=thisname)
                            rc = False
                        else:
                            if acfg.get('dispatch', False):
                                rc = self.dispatch(thisfunc, ask, acfg, tp.tag, jfile)
                                dispatched = True
                            else:
                                try:
                                    rc = apply(thisfunc, (ask,), ask.opts)
                                except StandardError as trouble:
                                    self.error('Trouble', action=ask.todo, error=trouble)
                                    rc = False
                    else:
                        self.warning('Inactive', action=ask.todo)
                        rctarget = 'ignore'
                else:
                    self.error('Unregistered', action=ask.todo)
                    rc = False
                    rctarget = 'ignore'
                if rc:
                    if not dispatched:
                        self.migrate(tp, jfile)
                else:
                    self.migrate(tp, jfile, target=rctarget)
        return rc

    def exit_callbacks(self):
        """Return a list of callbacks to be launch before daemon exit."""
        return (self.multi_stop, self.bye)

    def run(self):
        """Infinite work loop."""

        self.info('Just ask Jeeves...')

        self.multi_start()

        # migrate existing requests forgotten in processing directory
        thispool = pools.get(tag='process')
        todorun = thispool.contents
        if todorun:
            self.warning('Remaining requests', num=len(todorun))
            for bad in todorun:
                self.migrate(thispool, bad, target='retry')

        tprev = datetime.now()
        tbusy = False
        nbsleep = 0

        while True:

            tnext = datetime.now()
            ttime = ( tnext - tprev ).total_seconds()
            self.info('Loop', previous=ttime, busy=tbusy)
            tprev = tnext
            tbusy = False

            # do some cleaning to clear the place before real work
            for pool in pools.values():
                self.debug('Inspect', pool=pool.tag, path=pool.path, size=len(pool.contents), active=pool.active)
                pool.clean()

            # process the input pool first
            thispool = pools.get(tag='in')
            if thispool.active:
                self.debug('Processing', pool=thispool.tag, path=thispool.path)
                while thispool.contents:
                    tbusy = True
                    todo = sorted(thispool.contents)
                    # ignore some files with an explicit name
                    for bad in [ x for x in todo if 'ignore' in x ]:
                        tp = self.migrate(thispool, bad, target='ignore')
                        if tp is not None:
                            todo.remove(bad)
                    # look for config requests
                    for cfg in [ x for x in todo if x.endswith('.config.json') ]:
                        self.process_request(thispool, cfg)
                        todo.remove(cfg)
                    # look for other input requests
                    for req in todo[:]:
                        self.process_request(thispool, req)
                        todo.remove(req)
            else:
                self.warning('Inactive', pool=thispool.tag, path=thispool.path)

            # then process the retry pool
            thispool = pools.get(tag='retry')
            if thispool.active:
                self.debug('Processing', pool=thispool.tag, path=thispool.path)
                while thispool.contents:
                    tbusy = True
                    todo = sorted(thispool.contents)
                    # look for previous retry requests
                    for req in todo[:]:
                        self.process_request(thispool, req)
                        todo.remove(req)
            else:
                self.warning('Inactive', pool=thispool.tag, path=thispool.path)

            if not tbusy:
                nbsleep += 1
                time.sleep(min(nbsleep, self.config['driver'].get('maxsleep', 10)))
            else:
                nbsleep = 0

