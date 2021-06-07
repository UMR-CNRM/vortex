#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.util.worker import VortexWorker
from vortex.tools import compression, systems

#: No automatic export
__all__ = []


def _double_ssh(sh, loginnode, transfernode):
    """Applies a double ssh to retrieve the effective name of a machine.

    This trick enables the load balancing and node crash recovery
    capabilities handled by the network teams through DNS names.

    May return None when network problems occur.
    """
    cmd = ['ssh', '-x', loginnode, 'ssh', '-x', transfernode, 'hostname']
    rc = sh.spawn(cmd, shell=False, output=True, fatal=False)
    if not rc:
        return None
    return rc[0]


def system_ftput(pnum, ask, config, logger, **opts):
    """Ftp transfer to some archive host.

    Removes the source on success.
    In phase mode, raw ftp is not allowed, and the hostname is dynamically
    obtained by a double ssh.
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
        sh.ftpflavour = systems.FTP_FLAVOUR.STD  # Because errors are handled directly by jeeves

        data = vwork.get_dataset(ask)
        if phasemode:
            data.hostname = _double_ssh(sh, data.phase_loginnode, data.phase_transfernode)
            if data.hostname is None:
                return pnum, vwork.rc, value

        cpipeline = (None if not hasattr(data, 'cpipeline') or not data.cpipeline
                     else compression.CompressionPipeline(sh, data.cpipeline))

        logger.info('FTPut host', hostname=data.hostname, logname=data.logname)
        logger.info('FTPut data', source=data.source, destination=data.destination)
        while trynum < nbtries:
            trynum += 1
            if nbtries > 1:
                logger.info('FTPut loop', attempt=trynum)
            try:
                if rawftput:
                    putrc = sh.rawftput(data.source, data.destination, hostname=data.hostname,
                                        logname=data.logname, cpipeline=cpipeline,
                                        fmt=data.fmt)
                else:
                    putrc = sh.ftput(data.source, data.destination, hostname=data.hostname,
                                     logname=data.logname, cpipeline=cpipeline,
                                     fmt=data.fmt)
            except Exception as e:
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
        except Exception as e:
            logger.warning('cp failed', error=e)
            rc = False
        if rc:
            value = dict(clear=sh.rm(data.source, fmt=data.fmt))

    return pnum, vwork.rc, value


def system_scp(pnum, ask, config, logger, **opts):
    """Scp transfer to some archive host.

    Removes the source on success.
    In phase mode, raw ftp is not allowed, and the hostname is dynamically
    obtained by a double ssh.
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
        except Exception as e:
            logger.warning('scp failed', error=e)
            putrc = False
        if putrc:
            value = dict(clear=sh.rm(data.source, fmt=data.fmt))

    return pnum, vwork.rc, value


def system_noop(pnum, ask, config, logger, **opts):
    """A callback able to do nothing, but cleanly.

    Used to desactivate jeeves when mirroring the operational suite.
    """
    logger.info('Noop', todo=ask.todo, pnum=pnum, opts=opts)
    value = dict(rpool='error')

    with VortexWorker(logger=logger) as vwork:
        sh = vwork.vortex.sh()
        sh.trace = True
        data = vwork.get_dataset(ask)
        value = dict(clear=sh.rm(data.source, fmt=data.fmt))

    return pnum, vwork.rc, value


if __name__ == '__main__':
    import vortex

    t = vortex.ticket()
    sh = t.sh
    sh.trace = True
    sh.verbose = True
    print(_double_ssh(sh, 'beaufixoper', 'beaufixtransfert-agt'))
