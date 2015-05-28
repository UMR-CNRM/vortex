#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import fcntl
from vortex.util.worker import VortexWorker


class LockedOpen(object):
    def __init__(self, filename, mode):
        self.fp = open(filename, mode)

    @property
    def fid(self):
        return self.fp.fileno()

    def __enter__(self):
        fcntl.flock(self.fid, fcntl.LOCK_EX)
        return self.fp

    def __exit__(self, exc_type, exc_value, exc_traceback):
        fcntl.flock(self.fid, fcntl.LOCK_UN)
        self.fp.close()


def dayfile_report(pnum, ask, config, logger, **kw):
    """Standard old fashion reporting to messdayf daemon."""
    logger.info('dayfile_report', todo=ask.todo, pnum=pnum, opts=kw)
    value = None
    with VortexWorker(logger=logger) as vwork:
        logger.loglevel = 'debug'
        logger.debug('Vortex', todo=ask.todo, pnum=pnum, ticket=vwork.vortex.ticket().tag)
        sh = vwork.vortex.sh()
        data = vwork.get_dataset(ask)
        logger.debug('Reporting to', pnum=pnum, target=data.target)
        sh.filecocoon(data.target)
        with LockedOpen(data.target, 'a') as fp:
            fp.write(data.infos)
    return (pnum, vwork.rc, value)
