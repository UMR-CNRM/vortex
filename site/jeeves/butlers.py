# -*- coding: utf-8 -*-

"""
Daemon related classes:

- Generic base class for a daemon with pid file handling and a shareable logger
- HouseKeeping (internal configuration handling)

Jeeves inherits both of them and handles the asynchronous multiprocessing.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import fcntl
import io
import json
import multiprocessing
import os
import platform
import re
import resource
import signal
import subprocess
import sys
import time
from ast import literal_eval
from datetime import datetime
from signal import SIGTERM

import six
from six.moves.configparser import SafeConfigParser

from bronx.syntax import dictmerge, mktuple
from . import pools
from . import talking

#: No automatic export
__all__ = []

LOG_ARCHIVE_PATH = 'archive/log'


def _jeeves_import_module(modname, logger):
    """Import the module named ``modname`` with :mod:`importlib` package.

    :param modname: The module name
    :param logger: A logger object that will be used to comunicate
    :return: The module object or ``None`` if something goes wrong
    """
    if modname not in sys.modules:
        try:
            import importlib
        except ImportError as trouble:
            logger.critical('Importlib failed to load', exc_info=trouble)
            raise
        except Exception as trouble:
            logger.critical('Unexpected failure with importlib', exc_info=trouble)
            raise
        else:
            try:
                importlib.import_module(modname)
            except ImportError as trouble:
                logger.error('Could not import', module=modname, exc_info=trouble)
                return None
    return sys.modules.get(modname)


def _jeeves_callback_finder(thismod, thisname, logger):
    """Find and return the ``thisname`` callback in module ``thismode``.

    :param thismod: The module name
    :param thisname: The callback name (it must be a callable)
    :param logger: A logger object that will be used to comunicate
    :return: The object reprenting the callback or ``None`` if something goes wrong
    """
    thismobj = _jeeves_import_module(thismod, logger)
    if thismobj:
        thisfunc = getattr(thismobj, thisname, None)
        if thisfunc is None and not callable(thisfunc):
            logger.error('The callback is not a callable', funcname=thisname)
            thisfunc = None
    else:
        logger.error('Import failed', module=thismod)
        thisfunc = None
    if thisfunc is None:
        logger.error('The callback function was not found', funcname=thisname)
    return thisfunc


def _dispatch_func_wrapper(logger_cb, logger_setid_manager, loglevel,
                           modname, funcname, pnum, ask, config,
                           **kw):
    """
    Wrapper exexuted by the pool's worker in order to launch the callback
    ``funcname`` from module ``modname``.

    :param logger_cb: A callback that can be used to create logger objects
    :param logger_setid_manager: A context manager class that can be used
                                 to customise the logging system (in order
                                 to add the request ID (**pnum**)
    :param loglevel: The desired loglevel
    :param modname: The module name
    :param funcname: The callback name (it must be a callable)
    :param pnum: The request ID
    :param ask: The request itself
    :param config: The configuration section corresponding to this particular action
    :param kw: Any other parameter that will be passed to the callback
    :return: A three-element tuple (request ID, rc, extra_dictionary)
    """
    # Setup the logging system in order to display the request ID
    with logger_setid_manager(pnum, loglevel):
        my_logger = logger_cb(__name__)
        # Add extra layer of security (just in case an exception occurs)
        try:
            # Look for the desired callback
            func = _jeeves_callback_finder(modname, funcname, my_logger)
            if func is None:
                rc = (pnum, False, dict(rpool="error"))
            else:
                # Let's go !
                rc = func(pnum, ask, config, logger_cb(func.__module__), **kw)
        except Exception as trouble:
            my_logger.error("Un-handled exception in callback %s.", repr(func), exc_info=trouble)
            rc = (pnum, False, dict(rpool="error"))
        return rc


class ExitHandler(object):
    """Context manager for SIGTERM and Co. signals."""

    def __init__(self, daemon, on_exit=None, on_stack=False):
        self._on_stack = on_stack
        self._daemon = daemon
        try:
            on_exit[0]
        except TypeError:
            on_exit = (on_exit,)
        self._on_exit = tuple(on_exit)

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
        moreinfo = str(multiprocessing.current_process()) + ' ' + str(os.getpid())
        self.daemon.logger.info('Context enter for %s %s', repr(self.daemon), moreinfo)
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
        """Be sure to call all registered callbacks at exit time."""
        moreinfo = str(multiprocessing.current_process()) + ' ' + str(os.getpid())
        self.daemon.logger.info('Context exit for %s %s', repr(self.daemon), moreinfo)
        if exc_type is not None:
            if exc_type is SystemExit and exc_value.code == 0:
                self.daemon.logger.info('Context exit triggered by a clean sys.exit')
            else:
                self.daemon.logger.info('Context exit triggered by an exception.',
                                        exc_info=exc_value)
        for i, callback in enumerate([x for x in self.on_exit if x is not None]):
            self.daemon.logger.info('Context exit callback %d: %s', i, repr(callback))
            callback()
        return True


class PidFile(object):
    """
    Class in charge of pid handling in a simple file.
    """

    def __init__(self, tag='default', filename=None, procname='python'):
        if filename is None:
            node = re.sub(r'\..*', '', platform.node())
            filename = os.path.join(os.getcwd(), tag + '-' + node)
        if not filename.endswith('.pid'):
            filename += '.pid'
        self._filename = os.path.realpath(filename)
        self._procname = procname
        self.reset()

    def reset(self):
        """Create the pid file (would erase an older one) and lock it."""
        try:
            self._fd = os.open(self._filename, os.O_CREAT | os.O_RDWR, 0o644)
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
        """Unlock the pid file."""
        assert not fcntl.flock(self.fd, fcntl.LOCK_UN)

    def write(self, pid=None):
        """Write the pid in the (already open) file."""
        if pid is None:
            pid = os.getpid()
        os.ftruncate(self.fd, 0)
        os.write(self.fd, b"%d\n" % int(pid))
        os.fsync(self.fd)

    def delfile(self):
        """Remove actual pid filename."""
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def kill(self, retry=10):
        """Kill the process of which we handle the pid."""
        pid = int(os.read(self.fd, 4096))
        os.lseek(self.fd, 0, os.SEEK_SET)

        try:
            while retry > 0:
                os.kill(pid, SIGTERM)
                print('Sending SIGTERM to', pid, '...')
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
        """Is there a running process having the pid we handle."""
        contents = os.read(self.fd, 4096)
        os.lseek(self.fd, 0, os.SEEK_SET)

        if not contents:
            return False

        p = subprocess.Popen(
            ['ps', '-o', 'command', '-p', str(int(contents))],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, u_stderr = [six.ensure_text(stream) for stream in p.communicate()]
        if stdout == 'COMMAND\n':
            return False

        command = stdout[stdout.find("\n") + 1:]
        return self.procname in command and 'python' in command.lower()


class BaseDaemon(object):
    """
    A generic daemon class.
    Thanks to Sander Marechal : https://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    With some modifications and PidFile creation.

    Usage: subclass the BaseDaemon class and override the run() method
    """

    def __init__(self, tag='test', pidfile=None, procname='python', loglevel='INFO', inifile=None, redirect=None):
        self._tag = tag
        self._pidfile = PidFile(tag=tag, filename=pidfile, procname=procname)
        self._tmpdir = os.path.join(os.environ['HOME'], 'tmp')
        self._rundir = os.getcwd()
        self._logger = None
        self._logfacility = None
        self._loglevel = loglevel.upper()
        self._stdin = os.devnull
        node = re.sub(r'\..*', '', platform.node())
        self._redirect = os.path.realpath(redirect or tag + '-' + node + '.log')
        self._daemonized = False
        self._inifile = self._tag if inifile is None else inifile
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
        """The root loger loglevel."""
        return self._loglevel

    @loglevel.setter
    def loglevel(self, value):
        oldvalue = self._loglevel
        self._loglevel = value.upper()
        self._logger = None
        self.logger.warning('Jeeves loglevel changed from %s to %s. ' +
                            'This will only take effect when pool-workers restart.',
                            oldvalue, value.upper())

    @property
    def logfacility(self):
        """A LogFacility instance that provide the necessary features to deal with logging."""
        if self._logfacility is None:
            if six.PY2:
                self._logfacility = talking.LegacyLogfacility()
            else:
                self._logfacility = talking.LoggingBasedLogFacility()
        return self._logfacility

    @property
    def logger(self):
        """A logger instance for the daemon class."""
        if self._logger is None:
            self.logfacility.worker_log_setup(self.loglevel)
            self._logger = self.logfacility.worker_get_logger(__name__)
        return self._logger

    @property
    def inifile(self):
        return self._inifile

    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        https://www.oreilly.com/library/view/python-cookbook/0596001673/ch06s08.html
        https://gist.github.com/Ma233/dd1f2f93db5378a29a3d1848288f520e
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
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
        except OSError as e:
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
                except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                    pass

        # remap std 0, 1 and 2
        if self.daemonized:
            sys.stdin.close()
            sys.stdin = open(self.stdin, 'r')
        if self.stdout is not None:
            sys.stdout.flush()
            sys.stderr.flush()
            os.umask(0o0022)
            if self.stdout and os.path.exists(self.stdout):
                oldpath, oldname = os.path.split(self.stdout)
                newpath = os.path.join(oldpath, LOG_ARCHIVE_PATH)
                pools.parent_mkdir(newpath, mode=0o755)
                os.rename(self.stdout, os.path.join(
                    newpath, oldname + '.' + pools.timestamp()
                ))
            stdnew = open(self.stdout, 'a+', 1)
            os.dup2(stdnew.fileno(), sys.stdout.fileno())
            os.dup2(stdnew.fileno(), sys.stderr.fileno())

    def header(self):
        """Introduction to logging file..."""
        os.chdir(self.rundir)
        self.logger.info('Daemon', started=datetime.now())
        self.logger.info('Daemon', tag=self.tag)
        self.logger.info('Daemon', kind=self.__class__.__name__)
        self.logger.info('Daemon', module=self.__module__)
        self.logger.info('Process', pid=os.getpid())
        self.logger.info('Process', pidfile=self.pidfile.filename)
        self.logger.info('Process', rundir=self.rundir)
        self.logger.info('Process', tmpdir=self.tmpdir)
        self.logger.info('Process', python=sys.version.replace('\n', ' '))

    def bye(self):
        """Nice exit."""
        self.pidfile.delfile()
        self.logger.info('Bye folks...')

    def exit_callbacks(self):
        """Return a list of callbacks to be launched before the daemon exits."""
        return self.bye,

    def start(self, mkdaemon=True):
        """Start the daemon."""

        # check for a pidfile to see if the daemon already runs
        if self.pidfile.is_running():
            self.pidfile.unlock()
            sys.exit('Daemon already running.')

        # start the daemon
        print('Starting daemon...')
        if mkdaemon:
            self.daemonize()

        # write pidfile
        self.pidfile.write()
        self.pidfile.unlock()

        # gather std descriptors
        self.ioremap()

        # initialise the logging system
        with self.logfacility.log_infrastructure():

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
            print('Daemon not running.')
            return

        # try to nicely kill the daemon process
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
        raise NotImplementedError

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been daemonized by start() or restart() after setup().
        """
        raise NotImplementedError


class HouseKeeping(object):
    """A wrapper for all internal config callbacks."""

    def internal_reload(self, ask):
        """Proxy to a setup rerun."""
        if ask.data is None:
            self.logger.error('Reload undefined')
            return False
        else:
            self.multi_stop()
            if 'config' in ask.data:
                self.logger.warning('Rerun setup config')
                self.config = self.read_config(self.inifile)
            if 'mkpools' in ask.data:
                self.logger.warning('Rerun setup mkpools')
                self.mkpools(clear=True)
            self.multi_start()
            return True

    def internal_level(self, ask):
        """Set a specific log level."""
        self.loglevel = ask.data
        self.logger.warning('Reloading the process pool...')
        self.multi_stop(timeout=5)
        self.multi_start()
        return True

    def internal_sleep(self, ask):
        """Make a nap."""
        self.logger.warning('Sleep', duration=ask.data)
        time.sleep(ask.data)
        return True

    def internal_show(self, ask=None, actualcfg=None, scope='global'):
        """Display on stdout the current configuration."""
        if actualcfg is None:
            actualcfg = self.config
        conf_stack = list()
        conf_stack.append('-' * 80)
        conf_stack.append(scope.upper() + ' CONFIGURATION DISPLAY')
        conf_stack.append('-' * 80)
        for section, infos in sorted(actualcfg.items()):
            conf_stack.append('')
            conf_stack.append(' * ' + section)
            for k, v in sorted(infos.items()):
                conf_stack.append('   + {:<16s} = {!s}'.format(k, v))
        conf_stack.append('-' * 80)
        conf_stack.append('')
        self.logger.warning('Internal show result:\n%s', '\n'.join(conf_stack))
        return True

    def internal_update(self, ask):
        """Update the current configuration and display it."""
        if ask.data is not None and isinstance(ask.data, dict):
            self.internal_show(actualcfg=ask.data, scope='update')
            dictmerge(self.config, ask.data)
            return True
        else:
            self.logger.error('Not a valid update', data=type(ask.data))
            return False

    def internal_switch_pool(self, ask, status=False):
        """Update active parameters for pools."""
        for pool in [x.lower() for x in mktuple(ask.data)]:
            poolcfg = 'pool_' + pool
            if poolcfg in self.config:
                self.logger.warning('Switch pool', pool=pool, active=status)
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
        for action in [x.lower() for x in mktuple(ask.data)]:
            actioncfg = 'action_' + action
            if actioncfg not in self.config:
                self.config[actioncfg] = dict()
            self.logger.warning('Switch action', action=action, active=status)
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
        if os.path.exists(filename):
            absfile = os.path.abspath(filename)
            self.logger.info('Configuration', path=absfile)
            cfg = SafeConfigParser()
            cfg.read(absfile)

            self.logger.info('Configuration', sections=','.join(cfg.sections()))
            for section in cfg.sections():
                if section not in config:
                    config[section] = dict()
                for k, v in cfg.items(section):
                    try:
                        v = literal_eval(v)
                    except (SyntaxError, ValueError):
                        if k.startswith('options') or ',' in v:
                            v = [x for x in v.replace('\n', '').replace(' ', '').split(',')]
                    config[section][k.lower()] = v
        else:
            self.logger.error('No configuration', path=filename)
            sys.exit('No configuration (path={!s})'.format(filename))
        return config

    def mkpools(self, clear=False):
        """Create directories according to config file or default names."""
        if clear:
            pools.clear_all()
        for pool in self.config['driver'].get('pools', tuple()):
            poolcfg = 'pool_' + pool
            if poolcfg not in self.config:
                self.logger.warning('No dedicated conf', pool=pool)
                self.config[poolcfg] = dict()
            thispool = pools.get(tag=pool,
                                 logger=self.logfacility.worker_get_logger(pools.__name__),
                                 **self.config[poolcfg])

    def _get_pool(self, tag):
        if pools.check(tag):
            return pools.get(tag=tag)
        else:
            return pools.get(tag=tag,
                             logger=self.logfacility.worker_get_logger(pools.__name__))

    def setup(self):
        """
        Read any configuration file provided as tag.ini
        and create appropriate directories.
        """

        # read ini configuration file if any
        self.config = self.read_config(self.inifile)

        # check or create pool directories
        self.mkpools()

        # clean old log files
        keeplog = self.config['driver'].get('keeplog', '10d')
        pools.clean_older_files(self.logger, LOG_ARCHIVE_PATH, keeplog, '*.log.*')

    def _worker_init(self, logfacility):
        """Called each time a pool's worker is created/restarted"""
        logfacility.worker_log_setup(self.loglevel)
        me = multiprocessing.current_process()
        wlogger = logfacility.worker_get_logger(__name__)
        wlogger.info('PoolWorker initialising or restarting', pid=me.pid, realname=me.name)

    def multi_start(self):
        """Start a pool of co-workers processes."""
        self.ptask = 0
        self.asynchronous = dict()
        self.procs = self.config['driver'].get('maxprocs', 4)
        maxtasks = self.config['driver'].get('maxtasks', 64)
        self.ppool = multiprocessing.Pool(self.procs,
                                          self._worker_init,
                                          (self.logfacility, ),
                                          maxtasks)
        self.logger.info('Multiprocessing pool started', procs=self.procs)
        for child in sorted(multiprocessing.active_children(), key=lambda x: x.pid):
            self.logger.info('Coprocess', pid=child.pid, alive=child.is_alive(), name=child.name)
        return True

    def multi_stop(self, timeout=1):
        """Join all active coprocesses."""
        if hasattr(self, 'procs') and self.procs:
            # at least, some multiproccessing setup had occured
            self.logger.info('Terminate', procs=self.procs, remaining=len(self.asynchronous))

            # look at the remaining tasks
            for (pnum, syncinfo) in self.asynchronous.copy().items():
                self.logger.warning('Task not complete', pnum=pnum)
                try:
                    jpool, jfile, asyncr = syncinfo
                    pnum, prc, pvalue = asyncr.get(timeout=timeout)
                except multiprocessing.TimeoutError:
                    self.logger.error('Timeout for task', pnum=pnum)
                except Exception as trouble:
                    self.logger.critical('Trouble in pool', pnum=pnum, exc_info=trouble)
                else:
                    self.logger.info('Return', pnum=pnum, rc=prc, result=pvalue)
                    self.migrate(self._get_pool(jpool), jfile)
                finally:
                    del self.asynchronous[pnum]

            # try to clean the current active pool of processes
            try:
                self.ppool.close()
                self.ppool.terminate()
                self.ppool.join()
            except Exception as trouble:
                self.logger.critical('Multiprocessing stop failure.', exc_info=trouble)
        else:
            self.logger.warning('Multi stop without start ?')

        return True

    def migrate(self, pool, item, target=None):
        """Proxy to pool migration service."""
        rc = None
        try:
            target = pool.migrate(item, target=target)
            rc = self._get_pool(target)
        except OSError as trouble:
            self.logger.error('Could not migrate', item=item, exc_info=trouble)
        else:
            self.logger.info('Migrate', item=item, target=rc.path)
        return rc

    def json_load(self, pool, item):
        """Load a json request file."""
        obj = None
        jsonfile = os.path.join(pool.path, item)
        try:
            with io.open(jsonfile, 'rb') as fd:
                obj = json.load(fd)
            obj = pools.Request(**obj)
        except (ValueError, AttributeError, OSError):
            self.logger.error('Could not load', path=jsonfile, retry=self.redo.pop(item, 0))
            self.migrate(pool, item, target='error')
        return obj

    def async_callback(self, result):
        """Get result from async pool processing.

        Async callbacks should return a tuple (pnum, prc, pvalue):

        - pnum   = The unique id they received as first argument
        - prc    = True for success, False (or None) for failure
        - pvalue = a dict, may contain anything, but the key 'rpool' may be used to indicate
          in which pool the json request must be moved.

           - If the operation was successfull, the default target pool is taken from the
             configuration, e.g. pool_process ('run') -> pool_out ('done')
           - In case of failure, the default target is 'retry'. To send a request to the
             'error' pool, use pvalue = dict(rpool='error')
        """

        if not result:
            self.logger.error('Undefined result from asynchronous processing')
            return

        pnum = prc = pvalue = None
        try:
            pnum, prc, pvalue = result
            if prc:
                self.logger.info('Return', pnum=pnum, rc=prc, result=pvalue)
            else:
                self.logger.error('Return', pnum=pnum, rc=prc, result=pvalue)
        except Exception as trouble:
            self.logger.critical('Callback failed to process result', result=result, exc_info=trouble)
        finally:
            if pnum is not None and pnum in self.asynchronous:
                jpool, jfile, u_asyncr = self.asynchronous[pnum]
                poolbase = self._get_pool(jpool)
                pooltarget = None
                try:
                    pooltarget = pvalue.get('rpool', None)
                except AttributeError:
                    pass
                if not prc and pooltarget is None:
                    pooltarget = 'retry'
                self.migrate(poolbase, jfile, target=pooltarget)
                del self.asynchronous[pnum]
            else:
                self.logger.error('Unknown asynchronous process', pnum=pnum)

    def dispatch(self, modname, funcname, ask, acfg, jpool, jfile):
        """Multiprocessing dispatching."""
        rc = False
        self.ptask += 1
        pnum = '{0:06d}'.format(self.ptask)
        # complete the json opts with the configuration defaults
        opts = ask.opts.copy()
        for extra in [x for x in acfg.get('options', tuple()) if x not in opts]:
            opts[extra] = acfg.get(extra, None)
        try:
            self.asynchronous[pnum] = (
                jpool,
                jfile,
                self.ppool.apply_async(
                    func=_dispatch_func_wrapper,
                    args=(self.logfacility.worker_logger_cb,
                          self.logfacility.worker_logger_setid_manager,
                          acfg.get('loglevel', self.loglevel).upper(),
                          modname,
                          funcname,
                          pnum,
                          ask,
                          self.config.copy()),
                    kwds=opts,
                    callback=self.async_callback
                )
            )
        except Exception as trouble:
            self.logger.critical('Dispatch error', action=ask.todo, exc_info=trouble)
        else:
            rc = True
            self.logger.info('Dispatch', pnum=pnum, action=ask.todo)
        return rc

    def process_request(self, pool, jfile):
        """Process a standard request."""

        ask = self.json_load(pool, jfile)
        if ask is None:
            return False

        # tp = tag of the pool the jfile was migrated to
        tp = self.migrate(pool, jfile)
        if tp is None:
            return False

        if ask.todo not in self.config['driver'].get('actions', tuple()):
            self.logger.error('Unregistered', action=ask.todo)
            self.migrate(tp, jfile, target='ignore')
            return False

        rc = True
        dispatched = False
        rctarget = 'error'

        action = 'action_' + ask.todo
        if action in self.config:
            acfg = self.config[action]
        else:
            self.logger.debug('Undefined', action=ask.todo)
            acfg = dict(
                dispatch=False,
                module='internal',
                entry=ask.todo,
            )

        if acfg.get('active', True):
            thismod = acfg.get('module', 'internal')
            thisname = acfg.get('entry', ask.todo)
            self.logger.info(
                'Processing',
                action=ask.todo,
                function=thisname,
                module=thismod,
            )
            if thismod == 'internal' or not acfg.get('dispatch', False):
                # The internal or callback will be executed "in place"
                if thismod == 'internal':
                    thisfunc = getattr(self, 'internal_' + thisname, None)
                else:
                    thisfunc = _jeeves_callback_finder(thismod, thisname, self.logger)
                if thisfunc is None or not callable(thisfunc):
                    self.logger.error('The callback function was not found', funcname=thisname)
                    rc = False
                else:
                    try:
                        if thismod == 'internal':
                            rc = thisfunc(ask, **ask.opts)
                        else:
                            rc = thisfunc('000000',
                                          ask,
                                          self.config.copy(),
                                          self.logfacility.worker_get_logger(thisfunc.__module__))
                    except Exception as trouble:
                        self.logger.error('Trouble', action=ask.todo, exc_info=trouble)
                        rc = False
            else:
                # Delegate the execution to the process pool
                rc = self.dispatch(thismod, thisname, ask, acfg, tp.tag, jfile)
                dispatched = True

        else:
            self.logger.warning('Inactive', action=ask.todo)
            rctarget = 'ignore'

        if rc:
            if not dispatched:
                self.migrate(tp, jfile)
        else:
            self.migrate(tp, jfile, target=rctarget)

        return rc

    def exit_callbacks(self):
        """Return a list of callbacks to be launched before daemon exit."""
        return self.multi_stop, self.bye

    def run(self):
        """Infinite work loop."""

        self.logger.info('Just ask Jeeves...')
        self.multi_start()

        # migrate existing requests forgotten in processing directory
        thispool = self._get_pool('process')
        todorun = thispool.contents
        if todorun:
            self.logger.warning('Remaining requests', num=len(todorun))
            for bad in todorun:
                self.migrate(thispool, bad, target='retry')

        # setup default autoexit mode, once for all
        autoexit = self.config['driver'].get('autoexit', 0)
        self.logger.info('Automatic', autoexit=autoexit)

        # setup silent mode parameters
        maxsleep = self.config['driver'].get('maxsleep', 10)
        silent_delay = self.config['driver'].get('silent', 10)

        # initiate retry tracking
        self.redo = dict()
        rtinit = self.config['driver'].get('rtinit', 60)
        rtslow = self.config['driver'].get('rtslow', 2)
        rtceil = self.config['driver'].get('rtceil', 24 * 3600)
        rtstop = self.config['driver'].get('rtstop', 24 * 3600 * 5)

        tprev = datetime.now()
        tbusy = False
        nbsleep = 0
        silent = False
        working = True

        while working:

            tnext = datetime.now()
            ttime = (tnext - tprev).total_seconds()
            if not silent:
                self.logger.debug('Loop', previous=ttime, busy=tbusy, nbsleep=nbsleep)
            tprev = tnext
            tbusy = False

            # do some cleaning to clear the place before real work
            for pool in pools.values():
                pool.clean()

            # process the input pool first
            thispool = self._get_pool('in')
            if thispool.active:
                self.logger.debug('Processing', pool=thispool.tag, path=thispool.path)

                todo = thispool.contents
                while todo:
                    tbusy = True
                    # ignore some files with an explicit name
                    for bad in [x for x in todo if 'ignore' in x]:
                        tp = self.migrate(thispool, bad, target='ignore')
                        if tp is not None:
                            todo.remove(bad)
                    # look for config requests
                    for cfg in [x for x in todo if x.endswith('.config.json')]:
                        self.process_request(thispool, cfg)
                        todo.remove(cfg)
                    # look for other input requests
                    for req in todo:
                        self.process_request(thispool, req)
                    todo = thispool.contents
            else:
                self.logger.warning('Inactive', pool=thispool.tag, path=thispool.path)

            # then process the retry pool
            thispool = self._get_pool('retry')
            if thispool.active:
                self.logger.debug('Processing', pool=thispool.tag, path=thispool.path)
                # look for previous retry requests
                todo = thispool.contents
                stamp = datetime.now()
                for req in todo:
                    rt = self.redo.setdefault(req, dict(first=stamp, last=stamp, delay=rtinit, nbt=0))
                    rttotal = (stamp - rt['first']).total_seconds()
                    rtlast = (stamp - rt['last']).total_seconds()
                    if rttotal > rtstop:
                        tbusy = True
                        self.logger.warning('Abandonning retry', json=req, nbt=rt['nbt'], totaltime=rttotal)
                        self.migrate(thispool, req, target='error')
                        del self.redo[req]
                    elif rtlast > rt['delay']:
                        tbusy = True
                        rt['nbt'] += 1
                        rt['last'] = stamp
                        rt['delay'] = min(rtceil, max(1, int(rt['delay'] * rtslow)))
                        self.logger.warning('Retry', json=req, nbt=rt['nbt'], nextdelay=rt['delay'])
                        self.migrate(thispool, req)
            else:
                self.logger.warning('Inactive', pool=thispool.tag, path=thispool.path)

            if not tbusy:
                # nothing done... so handle sleeping mechanism.
                nbsleep += 1

                # check if we must exit from current session
                if autoexit and nbsleep > autoexit:
                    working = False
                    self.logger.warning('Stop', idle=autoexit)
                    continue

                # do not sleep more than the maxsleep config parameter (in seconds).
                time.sleep(min(nbsleep, maxsleep))
                if not silent and nbsleep > maxsleep:
                    if nbsleep - maxsleep >= silent_delay:
                        # we have been sleeping chunks of maxsleep seconds more that silent_delay times.
                        self.logger.warning('Enter silent mode', after=silent_delay)
                        silent = True
            else:
                # something has been done in this loop so... reset all sleeping mechanisms.
                nbsleep = 0
                silent = False
