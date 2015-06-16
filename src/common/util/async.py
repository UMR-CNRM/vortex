#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.util.worker import VortexWorker


def system_ftput(pnum, ask, config, logger, **opts):
    """Standard transfer to some archive host."""

    logger.info('System', todo=ask.todo, pnum=pnum, opts=opts)
    value = dict(rpool='retry')

    nbtries = opts.get('attempts', 1)
    trynum  = 0

    with VortexWorker(logger=logger) as vwork:
        sh = vwork.vortex.sh()
        sh.trace = True
        data = vwork.get_dataset(ask)
        logger.info('FTPut host', hostname=data.hostname, logname=data.logname)
        logger.info('FTPut data', source=data.source, destination=data.destination)
        while trynum < nbtries:
            trynum += 1
            if nbtries > 1:
                logger.info('FTPut loop', attempt=trynum)
            if sh.ftput(data.source, data.destination, hostname=data.hostname, logname=data.logname, fmt=data.fmt):
                value = dict(clear = sh.rm(data.source, fmt=data.fmt))
                break

    return (pnum, vwork.rc, value)
