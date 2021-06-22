#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This package defines a class for default contexts used
by a PoolWorker process of the Jeeves daemon.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from bronx.fancies import loggers

logger = loggers.getLogger(__name__)


class AttrDict(dict):
    """Dict object that can be accessed by attributes.

    >>> obj = AttrDict()
    >>> obj.test = 'hi'
    >>> print(obj['test'])
    hi

    >>> obj['test'] = "bye"
    >>> print(obj.test)
    bye

    >>> print(len(obj))
    1

    >>> obj.clear()
    >>> print(len(obj))
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
    """Context for a vortex session handled by an asynchronous process such as Jeeves.

    An _oper_ profile should be used from Jeeves: the default is to use a _research_ profile.
    See :mod:`vortex.gloves`.
    """

    _PRIVATESESSION_TAG = 'asyncworker_view'
    _PRIVATEGLOVE_TAG = 'asyncworker_id'
    _PRIVATESESSION = None
    _PRIVATEMODULES = set()

    def __init__(self, modules=tuple(), verbose=False, logger=None, profile=None,
                 logmap=('debug', 'info', 'warning'),
                 logmsg='Vortex context log gateway'):
        self._logger = logger
        self._logmap = logmap
        self._logmsg = logmsg
        self._modules = modules
        self._context_lock = False
        self._context_prev_ticket = None
        self.verbose = verbose
        self.profile = profile
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

    @property
    def session(self):
        """The session associated with Async Worker."""
        if self._PRIVATESESSION is None:
            import vortex
            t = vortex.sessions.get(
                tag=self._PRIVATESESSION_TAG,
                glove=vortex.sessions.getglove(
                    tag=self._PRIVATEGLOVE_TAG,
                    profile=self.profile
                )
            )
            sh = t.system()
            import vortex.tools.lfi  # @UnusedImport
            import vortex.tools.grib  # @UnusedImport
            import vortex.tools.folder  # @UnusedImport
            import footprints as fp
            fp.proxy.addon(kind='lfi', shell=sh)
            fp.proxy.addon(kind='grib', shell=sh)
            fp.proxy.addon(kind='allfolders', shell=sh, verboseload=False)
            self._PRIVATESESSION = t
        return self._PRIVATESESSION

    def get_dataset(self, ask):
        """Struct friendly access to data request."""
        return AttrDict(ask.data)

    def reset_loggers(self, logger):
        import footprints as fp
        loggers.setLogMethods(logger, methods=self.logmap)
        if self.verbose:
            fp.collectors.logger.debug(self.logmsg)
            fp.collectors.logger.info(self.logmsg)
            fp.collectors.logger.warning(self.logmsg)
            fp.collectors.logger.error(self.logmsg)
            fp.collectors.logger.critical(self.logmsg)

    def __enter__(self, *args):
        if self._context_lock:
            raise RuntimeError('Imbricated context manager calls are forbidden.')
        self._context_lock = True
        import vortex
        # Do questionable things on Vortex loggers
        if self.logger is None:
            self._logger = vortex.logger
        else:
            self.reset_loggers(self.logger)
        # Activate our own session
        self._context_prev_ticket = vortex.sessions.current()
        if not self.session.active:
            self.session.activate()
        # Import extra modules
        for modname in self.modules:
            if modname not in self._PRIVATEMODULES:
                self.session.sh.import_module(modname)
                self._PRIVATEMODULES.add(modname)
        # Ok, let's talk...
        self.logger.info('VORTEX enter glove_profile=%s modules=%s addons=%s ',
                         self.session.glove.profile,
                         str(self.modules), str(self.session.sh.loaded_addons()))
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Well... nothing much to do..."""
        if exc_value is not None:
            import traceback
            tb_sep = '-' * 80 + "\n"
            tb_str = str(exc_value) + "\n"
            if exc_value.message:
                tb_str += '{sep:s}Exception message: {exc.message:s}\n{sep:s}'.format(
                    sep=tb_sep, exc=exc_value
                )
            tb_str += '{sep:s}{tb:s}\n{sep:s}'.format(
                sep=tb_sep, tb=traceback.format_tb(exc_traceback)
            )
            self.logger.critical('VORTEX exits on error. Traceback gives:\n%s', tb_str)
            self.rc = False
        else:
            self.logger.info('VORTEX exits nicely.')
        self._context_prev_ticket.activate()
        self._context_lock = False
        return True


if __name__ == '__main__':
    import doctest

    doctest.testmod(verbose=False)
