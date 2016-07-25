#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package defines a class for default contexts used
by a PoolWorker process of the Jeeves daemon.
"""

import footprints
logger = footprints.loggers.getLogger(__name__)


class AttrDict(dict):
    """Dict object that can be accessed by attributes.

    >>> obj = AttrDict()
    >>> obj.test = 'hi'
    >>> print obj['test']
    hi

    >>> obj['test'] = "bye"
    >>> print obj.test
    bye

    >>> print len(obj)
    1

    >>> obj.clear()
    >>> print len(obj)
    0

    >>> obj.a
    Traceback (most recent call last):
        ...
    AttributeError: 'AttrDict' object has no attribute 'a'
    """

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class VortexWorker(object):
    """Context for a vortex session handled by an asynchronous process such as Jeeves."""

    def __init__(self, modules=tuple(), verbose=False, logger=None,
                 logmap=('debug', 'info', 'warning'),
                 logmsg='Vortex context log gateway'):
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

    def get_dataset(self, ask):
        """Struct friendly access to data request."""
        return AttrDict(ask.data)

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
        sh = vortex.sh()
        import vortex.tools.lfi
        import vortex.tools.odb
        import footprints as fp
        self.shlfi = fp.proxy.addon(kind='lfi', shell=sh)
        self.shodb = fp.proxy.addon(kind='odb', shell=sh)
        self.logger.warning('VORTEX enter ' + str(self.modules))
        for modname in self.modules:
            sh.import_module(modname)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Well... nothing much to do..."""
        if exc_value is not None:
            self.logger.critical('VORTEX exit', error=exc_value)
            import traceback
            print "\n", '-' * 80
            if exc_value.message:
                print exc_value.message
                print '-' * 80, "\n"
            print "\n".join(traceback.format_tb(exc_traceback))
            print '-' * 80, "\n"
            self.rc = False
        else:
            self.logger.warning('VORTEX exit')
        return True
