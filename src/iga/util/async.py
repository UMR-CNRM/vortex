# -*- coding: utf-8 -*-

"""
Callback functions for Jeeves, dedicated to operational needs.
If needed, VORTEX must be loaded via a VortexWorker in this context.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import fcntl
import io
import tempfile
from pprint import pformat

import six

from common.tools.grib import GRIBFilter
from footprints import proxy as fpx
from iga.tools import actions, services
from vortex.tools.actions import actiond as ad
from vortex.tools.net import uriparse
from vortex.util.worker import VortexWorker

#: No automatic export
__all__ = []

# prevent IDEs from removing seemingly unused imports
assert any([actions, services])


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

    profile = config['driver'].get('profile', None)
    with VortexWorker(logger=logger, profile=profile) as vwork:
        sh = vwork.session.sh
        logger.info('Vortex', todo=ask.todo, pnum=pnum, session=vwork.session.tag)
        data = vwork.get_dataset(ask)
        logger.debug('Reporting to', pnum=pnum, target=data.target)
        sh.filecocoon(data.target)
        with LockedOpen(data.target, 'a' + ('b' if six.PY2 else '')) as fp:
            fp.write(data.infos)
    return pnum, vwork.rc, value


def system_route(pnum, ask, config, logger, **opts):
    """Jeeves callback to filter and route a grib file.

    Removes the source on success (should be a hidden copy).
    """
    logger.info('System', todo=ask.todo, pnum=pnum, opts=opts)

    # options from the jeeves .ini configuration
    nossh = opts.get('nossh', False)
    route_on = opts.get('route_on', True)
    report_on = opts.get('report_on', True)

    profile = config['driver'].get('profile', None)
    with VortexWorker(logger=logger, verbose=True, profile=profile) as vwork:
        sh = vwork.session.sh
        sh.trace = False
        data = vwork.get_dataset(ask)

        # not before python3.2: tempfile.TemporaryDirectory
        tmpdir = tempfile.mkdtemp(prefix=data.source + '_', suffix='.tmp')
        with sh.cdcontext(tmpdir, create=True, clean_onexit=True):

            # assert the source is there
            logger.info('Source = ' + data.source)
            if not sh.path.exists(data.source):
                logger.warning('Source file is missing - trying to recover from the cache')
                uri = uriparse(data.rlocation)
                astore = fpx.store(**uri)
                astore.get(uri, data.source, dict(fmt=data.fmt))

            if not sh.path.exists(data.source):
                logger.error('The source file is definitely missing - sorry')
                return pnum, False, dict(rpool='error')

            # apply filtering, or at least ask for concatenation
            logger.info('filtername=' + (data.filtername or 'concatenation'))
            if data.filtername is None:
                gribfilter = GRIBFilter(concatenate=True)
            else:
                gribfilter = GRIBFilter(concatenate=False)
                gribfilter.add_filters(data.filterdefinition)
            outfile_fmt = 'GRIBOUTPUT_{filtername:s}.grib'
            filtered = gribfilter(data.source, outfile_fmt, intent='in')
            if len(filtered) != 1:
                logger.error('Should have 1 file in gribfilter output, got: %s', str(filtered))
                logger.error('Nothing will be routed, please fix the script.')
                return pnum, False, dict(rpool='error')
            route_source = filtered[0]

            # activate services or not according to jeeves' configuration
            if route_on:
                ad.route_on()
            else:
                ad.route_off()

            if report_on:
                ad.report_on()
            else:
                ad.report_off()

            # route the file
            route_opts = data.route_opts
            route_opts.update(
                filename=route_source,
            )
            if nossh:
                route_opts.update(
                    sshhost=None,
                )
            logger.info('Asking for route Services')
            logger.debug(pformat(route_opts))
            ad.route(**route_opts)

        return_value = dict(clear=sh.rm(data.source, fmt=data.fmt))

    return pnum, vwork.rc, return_value
