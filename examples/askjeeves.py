#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

def foo(pnum, ask, config, logger, **kw):
    rc, value = True, 'Yo'
    logger.info('External', todo=ask.todo, pnum=pnum, opts=kw)
    try:
        time.sleep(1)
    except StandardError as trouble:
        rc, value = False, str(trouble)
    return (pnum, rc, value)

class VortexContext(object):
    """Context for a vortex session handled by an asynchronous process such as Jeeves."""

    def __init__(self, modules=tuple(), verbose=False, logger=None, logmap=('debug', 'info', 'warning'), logmsg='Vortex context log gateway'):
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
        fp.loggers.setRootMethods(logger, methods=self.logmap)
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
        if exc_value.message:
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


def vortex_namespaces():
    print  "\n", '-' * 80, "\n"
    vortex.toolbox.print_namespaces()
    print  "\n", '-' * 80, "\n"

def test_vortex(pnum, ask, config, logger, **kw):
    value = 'Yip'
    with VortexContext(logger=logger, modules=('common',)) as vx:
        logger.info('Vortex', todo=ask.todo, pnum=pnum, ticket=vx.vortex.ticket().tag)
        logger.loglevel = 'debug'
        logger.debug('Ah que coucou')
    return (pnum, vx.rc, value)
