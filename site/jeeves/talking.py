"""
Everything related to log recording.
"""


import collections
import contextlib
import logging
import logging.handlers
import multiprocessing
import re
import sys
import traceback
from datetime import datetime

#: No automatic export
__all__ = []


# -----------------------------------------------------------------------------
# Abstract LogFacility

def _void_logger_cb(modname):
    """This should create a logger object."""
    raise NotImplementedError()


@contextlib.contextmanager
def _void_logger_setid_manager(taskno, loglevel):
    """This should configure the logging system in order to display the **taskno**"""
    raise NotImplementedError()


class AbstractLogFacility:
    """All the necessary features to handle logs in Jeeves"""

    @contextlib.contextmanager
    def log_infrastructure(self):
        """Setup the daemon's logging system backend."""
        yield

    def worker_log_setup(self, loglevel):
        """Setup the logging system for the daemon and workers."""
        pass

    @property
    def worker_logger_setid_manager(self):
        """
        Return a Context Manager class that will configure the logging system
        in order to display some kind of request ID.

        :note: A callback to an external function is used because the LogFacility
               class may not be picklable as a whole (which prevents us to use it
               directly with the multiprocessing.Pool).
        """
        return _void_logger_cb

    @property
    def worker_logger_cb(self):
        """Return a callback function that will return a logger for a given module name.

        :note: A callback to an external function is used because the LogFacility
               class may not be picklable as a whole (which prevents us to use it
               directly with the multiprocessing.Pool).
        """
        return _void_logger_cb

    def worker_get_logger(self, name=None):
        """A shortcut to create a logger (in the daemon process)."""
        return self.worker_logger_cb(name)


# -----------------------------------------------------------------------------
# The LogFacility based on the logging module (Python3 only)

# A few utility classes


class ShortenProcessName(logging.Filter):
    """A logging filter that makes the processName shorter."""

    _RE_WORKER = re.compile(r'.*PoolWorker.*-(\d+)$', re.IGNORECASE)
    _RE_MAIN = re.compile('MainProcess', re.IGNORECASE)

    def filter(self, record):
        wk_match = self._RE_WORKER.match(record.processName)
        if wk_match:
            record.processName = 'Worker-{:03d}'.format(int(wk_match.group(1)))
        else:
            if self._RE_MAIN.match(record.processName):
                record.processName = 'MainProc.'
        return True


class IdFilter(logging.Filter):
    """
    A logging Filter that adds some kind of request ID (**taskno**) to the
    log record message.
    """

    def __init__(self, taskno=None):
        super().__init__()
        self._id = taskno

    def filter(self, record):
        if self._id:
            record.msg = '[@{:s}] {:s}'.format(self._id, record.msg)
        return True


class FancyArgsLoggerAdapter(logging.LoggerAdapter):
    """
    Extend the traditional logger methods in order to support arbitrary keyword
    arguments.
    """

    _KW_PRESERVE = ('exc_info',)

    def process(self, msg, kwargs):
        msg += ' ' + ' '.join([
            '<' + k + ':' + str(v) + '>'
            for k, v in kwargs.items()
            if k not in self._KW_PRESERVE
        ])
        return msg, {k: v for k, v in kwargs.items() if k in self._KW_PRESERVE}


def _logging_based_logger_cb(name=None):
    """Create a logger object for the **name** module."""
    return FancyArgsLoggerAdapter(logging.getLogger(name), dict())


@contextlib.contextmanager
def _logging_logger_setid_manager(taskno, loglevel):
    """Configure the logging system in order to display the **taskno**"""
    root = logging.getLogger()
    # Tweak the loglevel
    prev_loglevel = root.level
    try:
        root.setLevel(loglevel)
    except ValueError:
        # Do not crash if an erroneous value is given. Just  do nothing
        pass
    # Filtering (that adds the task number)
    removed_filters = collections.defaultdict(list)
    current_filter = IdFilter(taskno)
    for h in root.handlers:
        for f in h.filters:
            if isinstance(f, IdFilter):
                removed_filters[h].append(f)
                h.removeFilter(f)
        h.addFilter(current_filter)
    try:
        yield
    finally:
        root.setLevel(prev_loglevel)
        for h in root.handlers:
            h.removeFilter(current_filter)
            for f in removed_filters[h]:
                h.addFilter(f)


class LoggingBasedLogFacility(AbstractLogFacility):
    """
    A "modern" LogFacility that setup and provide a logging system that is
    fully integrated with Python's logging module.
    """

    def __init__(self):
        self._log_queue = multiprocessing.Queue(-1)

    @staticmethod
    def _listener_configurer():
        """Create a StreamHandler that will actually write in the log file."""
        root = logging.getLogger()
        # Replace existing handlers
        for h in root.handlers:
            root.removeHandler(h)
        h = logging.StreamHandler()
        f = logging.Formatter('#[%(asctime)s]' +
                              '[%(processName)-10s:%(levelname)-8s] ' +
                              '%(message)s [from %(name)s.%(funcName)s:%(lineno)d]')
        h.setFormatter(f)
        h.addFilter(ShortenProcessName())
        root.addHandler(h)

    def _listener_process(self, log_queue):
        """
        The dedicated process that will listen to the **_log_queue** and emit
        log records to the Streamhandler.
        """
        self._listener_configurer()
        while True:
            try:
                record = log_queue.get()
                if record is None:  # We send this as a sentinel to tell the listener to quit.
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record)  # No level or filter logic applied - just do it!
            except Exception:
                print('Whoops! Logging problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    @contextlib.contextmanager
    def log_infrastructure(self):
        """Start a side process dedicated to the logging system."""
        listener = multiprocessing.Process(name='LogFacilityListener',
                                           target=self._listener_process,
                                           args=(self._log_queue,))
        listener.start()
        try:
            yield listener
        finally:
            self._log_queue.put_nowait(None)
            listener.join()

    def worker_log_setup(self, loglevel):
        """Setup the root logger in order to put log records in _log_queue."""
        root = logging.getLogger()
        # Replace existing handlers
        for h in root.handlers:
            root.removeHandler(h)
        root_h = logging.handlers.QueueHandler(self._log_queue)
        root.addHandler(root_h)
        # Logging level
        try:
            root.setLevel(loglevel)
        except ValueError:
            # Do not crash if an erroneous value is given. Just  do nothing
            pass

    @property
    def worker_logger_setid_manager(self):
        """
        Return a Context Manager class that will configure the logging system
        in order to display some kind of request ID.
        """
        return _logging_logger_setid_manager

    @property
    def worker_logger_cb(self):
        """Return a callback function that will return a logger for a given module name."""
        return _logging_based_logger_cb


# -----------------------------------------------------------------------------
# The legacy LogFacility (Python2 only)

class GentleTalk:
    """An alternative to the logging interface that can be exchanged between processes."""

    _levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

    DEBUG = '\033[94m'
    INFO = '\033[0m'
    WARNING = '\033[93m'
    ERROR = '\033[95m'
    CRITICAL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'

    def __init__(self, datefmt='%Y/%m/%d-%H:%M:%S', loglevel=1, taskno=0):
        self._datefmt = datefmt
        self._taskno = int(taskno)
        self.loglevel = loglevel

    def clone(self, taskno):
        """Clone the actual logger with a different task number."""
        return self.__class__(datefmt=self.datefmt, loglevel=self.loglevel, taskno=taskno)

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
        """
        @type value: int | str
        @rtype: None
        """
        try:
            value = int(value)
        except ValueError:
            try:
                value = self.levels.index(value.upper())
            except (AttributeError, ValueError):
                value = -1
        if 0 <= value <= len(self.levels):
            self._loglevel = value
        else:
            raise ValueError('Invalid loglevel: {!s}'.format(value))

    loglevel = property(_get_loglevel, _set_loglevel)

    @property
    def levelname(self):
        return self.levels[self._loglevel]

    def _msgfmt(self, level, msg, args, kw):
        """Formatting log message as `msg <key:value> ...` string."""
        if self.levels.index(level.upper()) >= self.loglevel:
            # older messages come with the '%' format syntax, newer with {}
            if args:
                if '%' in str(msg):
                    msg = str(msg) % args
                else:
                    msg = str(msg).format(*args)
            else:
                msg = str(msg)
            msg += ' ' + ' '.join([
                '<' + k + ':' + str(v) + '>'
                for k, v in kw.items()
            ])
            thisprocess = multiprocessing.current_process()
            msg = '{color}# [{0:s}][P{1:06d}][T{2:06d}][{3:13s}:{4:>8s}] {5:s}{endcolor}'.format(
                datetime.now().strftime(self.datefmt),
                thisprocess.pid,
                self.taskno,
                thisprocess.name,
                level.upper(),
                msg,
                color=getattr(self, level.upper()),
                endcolor=self.ENDC
            )
            with multiprocessing.Lock():
                print(msg)

    def debug(self, msg, *args, **kw):
        """Logger factorization."""
        return self._msgfmt('debug', msg, args, kw)

    def info(self, msg, *args, **kw):
        """Logger factorization."""
        return self._msgfmt('info', msg, args, kw)

    def warning(self, msg, *args, **kw):
        """Logger factorization."""
        return self._msgfmt('warning', msg, args, kw)

    def error(self, msg, *args, **kw):
        """Logger factorization."""
        return self._msgfmt('error', msg, args, kw)

    def critical(self, msg, *args, **kw):
        """Logger factorization."""
        return self._msgfmt('critical', msg, args, kw)


class GentleTalkMono(GentleTalk):
    """Monochrome version of the GentleTalk interface."""

    DEBUG = ''
    INFO = ''
    WARNING = ''
    ERROR = ''
    CRITICAL = ''
    ENDC = ''
    BOLD = ''
    HEADER = ''
    OKBLUE = ''
    OKGREEN = ''


#: The current GentleTalk object
root_gentle_talk = None


def _legacy_logger_cb(name=None):
    """Return the current GentleTalk object."""
    return root_gentle_talk


@contextlib.contextmanager
def _legacy_logger_setid_manager(taskno, loglevel):
    """Update the current GentleTask object qith the **taskno**."""
    global root_gentle_talk
    prev_root_gentle_talk = root_gentle_talk
    root_gentle_talk = GentleTalkMono(loglevel=loglevel, taskno=taskno)
    try:
        yield
    finally:
        root_gentle_talk = prev_root_gentle_talk


class LegacyLogfacility(AbstractLogFacility):
    """A legacy LogFacility relying on GentleTalk."""

    def worker_log_setup(self, loglevel):
        """Create a GentleTalk instance for future use."""
        global root_gentle_talk
        root_gentle_talk = GentleTalkMono(loglevel=loglevel,
                                          taskno=0)

    @property
    def worker_logger_setid_manager(self):
        """
        Return a Context Manager class that will configure the logging system
        in order to display some kind of request ID.
        """
        return _legacy_logger_setid_manager

    @property
    def worker_logger_cb(self):
        """Return a callback function that will return a logger."""
        return _legacy_logger_cb
