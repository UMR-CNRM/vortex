#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fabrik for root logger instances

#: No automatic export
__all__ = []

import logging

#: A default root name... that could be overwritten
defaultrootname = None

#: The actual set of pseudo-root loggers created
roots = set()

# Console handler
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(
    logging.Formatter(
        fmt = '# [%(asctime)s][%(name)s][%(funcName)s:%(lineno)d][%(levelname)s]: %(message)s',
        datefmt = '%Y/%d/%m-%H:%M:%S',
    )
)

# A hook filter (optional)
class LoggingFilter(logging.Filter):
    """Add module name to record."""

    def filter(self, record):
        print 'FILTER', record.msg
        if record.funcName == '<module>':
            record.funcName = 'prompt'
        return True


def getRootLogger(name, level=logging.INFO):
    """Build a new top level logger."""
    thislogger = logging.getLogger(name)
    thislogger.setLevel(level)
    thislogger.addHandler(console)
    thislogger.addFilter(LoggingFilter(name=name))
    roots.add(name)
    return thislogger


def getLogger(modname, rootname=None):
    """Return an adapter on a matching root logger previously defined."""
    actualroot = rootname or defaultrootname or modname.split('.')[0]
    if actualroot in roots:
        rootlogger = logging.getLogger(actualroot)
    else:
        rootlogger = getRootLogger(actualroot)
    if actualroot == modname:
        return rootlogger
    else:
        return logging.getLogger(modname)
