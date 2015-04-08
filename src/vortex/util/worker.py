#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package defines a class for default contexts used
by a PoolWorker process of the Jeeves daemon.
"""

import footprints
logger = footprints.loggers.getLogger(__name__)


class VortexWorker(object):
    """Context for a vortex session handled by an asynchronous process such as Jeeves."""

    def __init__(self, modules=tuple(), verbose=False,
        logger=None,
        logmap=('debug', 'info', 'warning'),
        logmsg='Vortex context log gateway'
    ):
        self._logger  = logger
        self._logmap  = logmap
        self._logmsg  = logmsg
        self._modules = modules
        self.verbose = verbose
        self.rc = True

    @property
    def logger(self):
        return self._logger

    @property
    def logmap(self):
        return self._logmap

    @property
    def logmsg(self):
        return self._logmsg

    @property
    def modules(self):
        return self._modules

    def reset_loggers(self, logger):
        import footprints as fp
        fp.loggers.setLogMethods(logger, methods=self.logmap)
        if self.verbose:
            fp.collectors.logger.debug(self.logmsg)
            fp.collectors.logger.info(self.logmsg)
            fp.collectors.logger.warning(self.logmsg)
            fp.collectors.logger.error(self.logmsg)
            fp.collectors.logger.critical(self.logmsg)

    def __enter__(self, *args):
        import vortex
        self.vortex = vortex
        if self.logger is None:
            self._logger = vortex.logger
        else:
            self.reset_loggers(self.logger)
        self.logger.warning('VORTEX enter ' + str(self.modules))
        sh = vortex.sh()
        for modname in self.modules:
            sh.import_module(modname)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Well... nothing much to do..."""
        if exc_value is not None and exc_value.message:
            self.logger.critical('VORTEX exit', error=exc_value)
            import traceback
            print "\n", '-' * 80
            print exc_value.message
            print '-' * 80, "\n"
            print "\n".join(traceback.format_tb(exc_traceback))
            print '-' * 80, "\n"
            self.rc = False
        else:
            self.logger.warning('VORTEX exit')
        return True
