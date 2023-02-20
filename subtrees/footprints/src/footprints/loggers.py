"""
This module provides a few functions on top of the standard logging module in
order to easily create new loggers (including root ones) and control their
verbosity level.


It is kept for backward compatibility, however :mod:`bronx.fancies.loggers` should
be used now and on.
"""

import sys

# For backward compatibility
import logging  # @UnusedImport

from bronx.fancies import loggers as _b_loggers

assert logging

_ALIASES = dict()
_ALIASES.update(dict(roots=_b_loggers.roots,
                     lognames=_b_loggers.lognames,
                     formats=_b_loggers.predefined_formats,
                     console=_b_loggers.default_console,
                     getLogger=_b_loggers.getLogger,
                     setGlobalLevel=_b_loggers.setGlobalLevel,
                     setRootLogger=_b_loggers.setRootLogger,
                     setLogMethods=_b_loggers.setLogMethods,
                     getActualLevel=_b_loggers.getActualLevel,
                     LoggingFilter=_b_loggers.PromptAwareLoggingFilter,
                     SlurpHandler=_b_loggers.SlurpHandler,
                     )
                )

for n, obj in _ALIASES.items():
    sys.modules[__name__].__dict__.update(_ALIASES)
