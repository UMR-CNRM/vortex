#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo import mpitools


class NecMpiRun(mpitools.MpiRun):
    """MPIRUN utility on NEC SX systems."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values = [ 'SUPER-UX' ]
            ),
        )
    )

    def setup(self, opts=None):
        """
        Prepares automatic export of variables through the MPIEXPORT mechanism.
        The list of variables could be extended or reduced through:

         * MPIRUN_FILTER
         * MPIRUN_DISCARD
        """

        super(NecMpiRun, self).setup(opts)

        e = self.env

        if not e.false('mpirun_export'):
            if 'mpiexport' in e:
                mpix = set(e.mpiexport.split(','))
            else:
                mpix = set()

            if not e.false('mpirun_filter'):
                mpifilter = re.sub(',', '|', e.mpirun_filter)
                mpix.update(filter(lambda x: re.match(mpifilter, x), e.keys()))

            if not e.false('mpirun_discard'):
                mpidiscard = re.sub(',', '|', e.mpirun_discard)
                mpix = set(filter(lambda x: not re.match(mpidiscard, x), mpix))

            e.mpiexport = ','.join(mpix)
            logger.debug('MPI export environment %s', e.mpiexport)


class MpiAuto(mpitools.MpiRun):
    """Standard MPI launcher on most systems."""

    _footprint = dict(
        attr = dict(
            mpiname = dict(
                values = [ 'mpiauto' ],
            ),
            mpiopts = dict(
                default = '--wrap --wrap-stdeo --wrap-stdeo-pack --verbose',
            ),
            optprefix = dict(
                default = '--'
            )
        )
    )


class MpiNWPIO(mpitools.MpiServerIO):
    """Standard IFS NWP IO server."""

    _footprint = dict(
        attr = dict(
            pattern = dict(
                optional = True,
                default  = 'io_serv.*.d',
            ),
            polling = dict(
                type     = bool,
                optional = True,
                default  = False,
                access   = 'rwx',
            )
        )
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying IO Serveur profile on local namelist ``namlocal`` with contents namcontents."""
        if 'NAMIO_SERV' in namcontents:
            namio = namcontents['NAMIO_SERV']
        else:
            namio = namcontents.newblock('NAMIO_SERV')

        namio.nproc_io = self.nprocs

        if 'VORTEX_IOSERVER_METHOD'   in self.env:
            namio.nio_serv_method      = self.env.VORTEX_IOSERVER_METHOD

        if 'VORTEX_IOSERVER_BUFMAX'   in self.env:
            namio.nio_serv_buf_maxsize = self.env.VORTEX_IOSERVER_BUFMAX

        if 'VORTEX_IOSERVER_MLSERVER' in self.env:
            namio.nmsg_level_server    = self.env.VORTEX_IOSERVER_MLSERVER

        if 'VORTEX_IOSERVER_MLCLIENT' in self.env:
            namio.nmsg_level_client    = self.env.VORTEX_IOSERVER_MLCLIENT

        if 'VORTEX_IOSERVER_PROCESS'  in self.env:
            namio.nprocess_level       = self.env.VORTEX_IOSERVER_PROCESS

        if 'VORTEX_IOSERVER_PIOMODEL' in self.env:
            namio.pioprocr_MDL         = self.env.VORTEX_IOSERVER_PIOMODEL

        self.system.subtitle('Parallel io namelist')
        print namio.dumps()

        return True

    def iodirs(self):
        """Return an ordered list of directories matching the ``pattern`` attribute."""
        return sorted(self.system.glob(self.pattern))

    def clean(self, opts=None):
        """Post-execution cleaning for io server."""
        self.polling = True

        # Old fashion way to make clear that some polling is needed.
        self.system.touch('io_poll.todo')

        # Get a look inside io server output directories according to its own pattern
        for iodir in self.iodirs():
            self.system.subtitle('Parallel io directory {0:s}'.format(iodir))
            self.system.ls('-l', iodir, output=False)
            for iofile in self.system.ls(iodir):
                zf = re.match('((?:ICMSH|PF).*\+\d+)(?:\..*)?$', iofile)
                if zf:
                    tgfile = zf.group(1)
                    if not self.system.path.exists(tgfile):
                        self.system.touch(tgfile)
