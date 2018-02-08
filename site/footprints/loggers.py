#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

# Fabrik for root logger instances

import logging

#: No automatic export
__all__ = []

#: The actual set of pseudo-root loggers created
roots = set()
lognames = set()

#: Default formatters
formats = dict(
    default = logging.Formatter(
        fmt = '# [%(asctime)s][%(name)s][%(funcName)s:%(lineno)04d][%(levelname)s]: %(message)s',
        datefmt = '%Y/%m/%d-%H:%M:%S',
    ),
    fixsize = logging.Formatter(
        fmt = '# [%(asctime)s][%(name)-24s][%(funcName)16s:%(lineno)04d][%(levelname)9s]: %(message)s',
        datefmt = '%Y/%m/%d-%H:%M:%S',
    ),
)

#: Console handler
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formats['default'])


# A hook filter (optional)
class LoggingFilter(logging.Filter):
    """Add module name to record."""

    def filter(self, record):
        """Remap top interactive module to ``prompt``."""
        if record.funcName == '<module>':
            record.funcName = 'prompt'
        return True


def setRootLogger(logger, level=logging.INFO):
    """Set appropriate Handler and Console to a top level logger."""
    logger.setLevel(level)
    logger.addHandler(console)
    logger.addFilter(LoggingFilter(name=logger.name))
    logger.propagate = False
    roots.add(logger.name)
    return logger


def getLogger(modname):
    """Return a standard logger in the scope of an appropriate root logger."""
    rootname = modname.split('.')[0]
    rootlogger = logging.getLogger(rootname)
    if rootname not in roots:
        setRootLogger(rootlogger)
    lognames.add(modname)
    if rootname == modname:
        return rootlogger
    else:
        return logging.getLogger(modname)


def setLogMethods(logger, methods=('debug', 'info', 'warning', 'error', 'critical')):
    """Reset some loggers methods with methods from an external logger."""
    for modname in lognames:
        thislog = logging.getLogger(modname)
        for logmethod in methods:
            setattr(thislog, logmethod, getattr(logger, logmethod))


def getActualLevel(level):
    """Return the actual level value as long as the argument is valid."""
    if type(level) is int:
        if level not in logging._levelNames:
            level = None
    else:
        level = logging._levelNames.get(level.upper())
    return level


def setGlobalLevel(level):
    """
    Explicitly sets the logging level to the ``level`` value for all roots items.
    """
    thislevel = getActualLevel(level)
    if thislevel is None:
        logger.error('Try to set an unknown log level <%s>', level)
    else:
        for rootname in roots:
            r_logger = logging.getLogger(rootname)
            r_logger.setLevel(thislevel)
    return thislevel


class SlurpHandler(logging.Handler):
    """A strange Handler that accumulates the log-records in a list.

    We try to make sure that each individual record is pickable.
    """

    def __init__(self, records_stack):
        super(SlurpHandler, self).__init__()
        self._stack = records_stack

    def prepare(self, record):
        """
        Prepares a record for queuing.

        The base implementation formats the record to merge the message
        and arguments, and removes unpickleable items from the record
        in-place.

        :param record: The record to prepare.
        """
        self.format(record)
        record.msg = record.message
        record.args = None
        record.exc_info = None
        return record

    def emit(self, record):
        """
        Emit a record.

        Adds the LogRecord to the stack, preparing it for pickling first.

        :param record: The record to emit.
        """
        try:
            self._stack.append(self.prepare(record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
