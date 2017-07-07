#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.util.worker import VortexWorker

#: No automatic export
__all__ = []


def _double_ssh(sh, loginnode, transfernode):
    """Applies a double ssh to retrieve the effective name of a machine.
       This trick enables the load balancing and node crash recovery
       capabilities handled by the network teams through DNS names.
       May return None when network problems occur.
    """
    cmd = 'ssh {} ssh {} hostname'.format(loginnode, transfernode)
    rc = sh.spawn(cmd, shell=True, output=True, fatal=False)
    if not rc:
        return None
    return rc[0]


def system_ftput(pnum, ask, config, logger, **opts):
    """Ftp transfer to some archive host.
       Removes the source on success.
       In phase mode, raw ftp is not allowed, and the hostname
       is dynamically obtained by a double ssh.
    """

    logger.info('System', todo=ask.todo, pnum=pnum, opts=opts)
    value = dict(rpool='retry')

    phasemode = opts.get('phasemode', False)
    nbtries = opts.get('attempts', 1)
    if phasemode:
        rawftput = False
    else:
        rawftput = opts.get('rawftput', False)
    trynum = 0

    with VortexWorker(logger=logger) as vwork:
        sh = vwork.vortex.sh()
        sh.trace = False

        data = vwork.get_dataset(ask)
        if phasemode:
            data.hostname = _double_ssh(sh, data.phase_loginnode, data.phase_transfernode)
            if data.hostname is None:
                return pnum, vwork.rc, value

        logger.info('FTPut host', hostname=data.hostname, logname=data.logname)
        logger.info('FTPut data', source=data.source, destination=data.destination)
        while trynum < nbtries:
            trynum += 1
            if nbtries > 1:
                logger.info('FTPut loop', attempt=trynum)
            try:
                if rawftput:
                    putrc = sh.rawftput(data.source, data.destination, hostname=data.hostname,
                                        logname=data.logname, cpipeline=data.cpipeline,
                                        fmt=data.fmt)
                else:
                    putrc = sh.ftput(data.source, data.destination, hostname=data.hostname,
                                     logname=data.logname, cpipeline=data.cpipeline,
                                     fmt=data.fmt)
            except StandardError as e:
                logger.warning('FTPut failed', attempt=trynum, error=e)
                putrc = False
            if putrc:
                value = dict(clear=sh.rm(data.source, fmt=data.fmt))
                break

    return pnum, vwork.rc, value


def system_cp(pnum, ask, config, logger, **opts):
    """Local transfers (between filesystems) on a given host."""

    logger.info('System', todo=ask.todo, pnum=pnum, opts=opts)
    value = dict(rpool='retry')

    with VortexWorker(logger=logger) as vwork:
        sh = vwork.vortex.sh()
        sh.trace = True
        data = vwork.get_dataset(ask)
        logger.info('cp', source=data.source, destination=data.destination)
        try:
            rc = sh.cp(data.source, data.destination, fmt=data.fmt)
        except StandardError as e:
            logger.warning('cp failed', error=e)
            rc = False
        if rc:
            value = dict(clear=sh.rm(data.source, fmt=data.fmt))

    return pnum, vwork.rc, value


def system_scp(pnum, ask, config, logger, **opts):
    """Scp transfer to some archive host.
       Removes the source on success.
       In phase mode, raw ftp is not allowed, and the hostname
       is dynamically obtained by a double ssh.
    """
    logger.info('System', todo=ask.todo, pnum=pnum, opts=opts)
    value = dict(rpool='retry')

    phasemode = opts.get('phasemode', False)

    with VortexWorker(logger=logger) as vwork:
        sh = vwork.vortex.sh()
        sh.trace = True

        data = vwork.get_dataset(ask)
        if phasemode:
            data.hostname = _double_ssh(sh, data.phase_loginnode, data.phase_transfernode)
            if data.hostname is None:
                return pnum, vwork.rc, value
        logger.info('scp host', hostname=data.hostname, logname=data.logname)
        logger.info('scp data', source=data.source, destination=data.destination)
        try:
            putrc = sh.scpput(data.source, data.destination, hostname=data.hostname,
                              logname=data.logname, fmt=data.fmt)
        except StandardError as e:
            logger.warning('scp failed', error=e)
            putrc = False
        if putrc:
            value = dict(clear=sh.rm(data.source, fmt=data.fmt))

    return pnum, vwork.rc, value
