#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Fabrik for root logger instances

#: No automatic export
__all__ = []

import logging

#: The actual set of pseudo-root loggers created
roots = set()

#: Console handler
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
        if record.funcName == '<module>':
            record.funcName = 'prompt'
        return True


def setRootLogger(logger, level=logging.INFO):
    """Set appropriate Handler and Console to a top level logger."""
    logger.setLevel(level)
    logger.addHandler(console)
    logger.addFilter(LoggingFilter(name=logger.name))
    roots.add(logger.name)
    return logger


def getLogger(modname):
    """Return a standard logger in the scope of an appropriate root logger."""
    rootname = modname.split('.')[0]
    rootlogger = logging.getLogger(rootname)
    if rootname not in roots:
        setRootLogger(rootlogger)
    if rootname == modname:
        return rootlogger
    else:
        return logging.getLogger(modname)
