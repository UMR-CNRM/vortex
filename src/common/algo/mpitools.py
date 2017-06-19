#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo import mpitools
from vortex.syntax.stdattrs import DelayedEnvValue


class MpiAuto(mpitools.MpiTool):
    """MpiTools that uses mpiauto as a proxy to several MPI implementations"""

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
            ),
            optmap = dict(
                default  = footprints.FPDict(nn='nn', nnp='nnp', openmp='openmp',
                                             np='np', prefixcommand='prefix-command',
                                             allowodddist='mpi-allow-odd-dist')
            ),
            timeoutrestart = dict(
                info            = 'The number of attempts made by mpiauto',
                optional        = True,
                default         = DelayedEnvValue('MPI_INIT_TIMEOUT_RESTART', 2),
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
        )
    )

    def _reshaped_mpiopts(self):
        """Raw list of mpi tool command line options."""
        options = super(MpiAuto, self)._reshaped_mpiopts()
        options['init-timeout-restart'] = self.timeoutrestart
        return options

    def _hook_binary_mpiopts(self, options):
        tuned = options.copy()
        # Regular MPI tasks count (the usual...)
        if 'nnp' in options and 'nn' in options:
            if options['nn'] * options['nnp'] == options['np']:
                # Remove harmlful options
                del tuned['np']
                tuned.pop('allowodddist', None)
                # that's the strange MPI distribution...
            else:
                tuned['allowodddist'] = None  # With this, let mpiauto determine its own partitioning
        else:
            msg = ("The provided mpiopts are insufficient to build the command line: {!s}"
                   .format(options))
            raise mpitools.MpiException(msg)
        return tuned

    def setup(self, opts=None):
        """Ensure that the prefixcommand has the execution rights."""
        super(MpiAuto, self).setup(opts)
        prefix_c = self._reshaped_mpiopts().get('prefixcommand', None)
        if prefix_c is not None:
            if self.system.path.exists(prefix_c):
                self.system.xperm(prefix_c, force=True)
            else:
                raise IOError('The prefixcommand do not exists.')


class MpiNWP(mpitools.MpiBinaryBasic):
    """The kind of binaries used in NWP"""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['basicnwp', ],
            ),
        ),
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying MPI profile on local namelist ``namlocal`` with contents namcontents."""
        namw = super(MpiNWP, self).setup_namelist_delta(namcontents, namlocal)
        if ('NBPROC' in namcontents.macros() or 'NPROC' in namcontents.macros()):
            namcontents.setmacro('NCPROC', int(self.env.VORTEX_NPRGPNS or self.nprocs))
            namcontents.setmacro('NDPROC', int(self.env.VORTEX_NPRGPEW or 1))
            namw = True
        if 'NAMPAR1' in namcontents:
            np1 = namcontents['NAMPAR1']
            for nstr in [ x for x in ('NSTRIN', 'NSTROUT') if x in np1 ]:
                if np1[nstr] > self.nprocs:
                    logger.info('Setup %s=%s in NAMPAR1 %s', nstr, self.nprocs, namlocal)
                    np1[nstr] = self.nprocs
                    namw = True
        return namw


class MpiNWPIO(mpitools.MpiBinaryIOServer):
    """Standard IFS NWP IO server."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['nwpioserv', ],
            ),
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
        ioserv_filelist = set()
        ioserv_prefixes = set()
        logfmt = '%24s: %32s %s'
        iofile_re = re.compile(r'((ICMSH|PF|GRIBPF).*\+\d+(?:\:\d+)?(?:\.sfx)?)(?:\..+)?$')
        for iodir in self.iodirs():
            self.system.subtitle('Parallel io directory {0:s}'.format(iodir))
            for iofile in self.system.listdir(iodir):
                zf = iofile_re.match(iofile)
                if zf:
                    logger.info(logfmt, iodir, iofile, ':-)')
                    ioserv_filelist.add(zf.group(1))
                    ioserv_prefixes.add(zf.group(2))
                else:
                    logger.info(logfmt, iodir, iofile, 'UFO')

        # Touch the output files
        for tgfile in ioserv_filelist:
            self.system.touch(tgfile)

        # Touch the io_poll.todo.PREFIX
        for prefix in ioserv_prefixes:
            self.system.touch('io_poll.todo.{:s}'.format(prefix))
