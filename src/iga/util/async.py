# -*- coding: utf-8 -*-

"""
TODO: module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import fcntl
import io
from vortex.util.worker import VortexWorker

#: No automatic export
__all__ = []


class LockedOpen(object):
    """Context class for locking a file while it is open."""
    def __init__(self, filename, mode):
        self.fp = io.open(filename, mode)

    @property
    def fid(self):
        return self.fp.fileno()

    def __enter__(self):
        """Called when entering the context: lock the file."""
        fcntl.flock(self.fid, fcntl.LOCK_EX)
        return self.fp

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Called when leaving the context: unlock and close the file."""
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
        with LockedOpen(data.target, 'a' + ('b' if six.PY2 else '')) as fp:
            fp.write(data.infos)
    return (pnum, vwork.rc, value)
