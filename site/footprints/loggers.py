#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fabrik for root logger instances

#: No automatic export
__all__ = []

import logging

#: The actual set of pseudo-root loggers created
roots = set()
lognames = set()

#: Default formatters
formats = dict(
    default = logging.Formatter(
        fmt = '# [%(asctime)s][%(name)s][%(funcName)s:%(lineno)04d][%(levelname)s]: %(message)s',
        datefmt = '%Y/%d/%m-%H:%M:%S',
    ),
    fixsize = logging.Formatter(
        fmt = '# [%(asctime)s][%(name)-24s][%(funcName)16s:%(lineno)04d][%(levelname)9s]: %(message)s',
        datefmt = '%Y/%d/%m-%H:%M:%S',
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
