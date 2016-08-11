#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import Parallel
from vortex.tools import grib


class IFSParallel(Parallel, grib.GribApiComponent):
    """Abstract IFSModel parallel algo components."""

    _abstract = True
    _footprint = dict(
        info = 'Abstract AlgoComponent for anything based on Arpege/IFS.',
        attr = dict(
            kind = dict(
                info            = 'The kind of processing we want the Arpege/IFS binary to perform.',
                default         = 'ifsrun',
                doc_zorder      = 90,
            ),
            conf = dict(
                info = 'The configuration number given to Arpege/IFS.',
                type            = int,
                optional        = True,
                default         = 1,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            timescheme = dict(
                info = 'The timescheme that will be used by Arpege/IFS model.',
                optional        = True,
                default         = 'sli',
                values          = ['eul', 'eulerian', 'sli', 'semilag'],
                remap           = dict(
                    eulerian = 'eul',
                    semilag  = 'sli'
                ),
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            timestep = dict(
                info     = 'The timestep of the Arpege/IFS model.',
                type     = float,
                optional = True,
                default  = 600.,
            ),
            fcterm = dict(
                info     = 'The forecast term of the Arpege/IFS model.',
                type = int,
                optional = True,
                default = 0,
            ),
            fcunit = dict(
                info     = 'The unit used in the *fcterm* attribute.',
                optional = True,
                default  = 'h',
                values   = ['h', 'hour', 't', 'step'],
                remap = dict(
                    hour = 'h',
                    step = 't'
                )
            ),
            xpname = dict(
                info = 'The default labelling of files used in Arpege/IFS model.',
                optional        = True,
                default         = 'XPVT',
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            drhookprof = dict(
                info            = 'Activate the DrHook profiling.',
                optional        = True,
                type            = bool,
                default         = False,
                doc_zorder      = -50,
            ),
            member = dict(
                info            = ("The current member's number " +
                                   "(may be omitted in deterministic configurations)."),
                optional        = True,
                type            = int,
            ),
        )
    )

    def fstag(self):
        """Extend default tag with ``kind`` value."""
        return super(IFSParallel, self).fstag() + '.' + self.kind

    def valid_executable(self, rh):
        """Be sure that the specifed executable is ifsmodel compatible."""
        try:
            return bool(rh.resource.realkind == 'ifsmodel')
        except (ValueError, TypeError):
            return False

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super(IFSParallel, self).spawn_hook()
        if self.system.path.exists('fort.4'):
            self.system.subtitle('{0:s} : dump namelist <fort.4>'.format(self.realkind))
            self.system.cat('fort.4', output=False)

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            name       = (self.xpname + 'xxxx')[:4].upper(),
            conf       = self.conf,
            timescheme = self.timescheme,
            timestep   = self.timestep,
            fcterm     = self.fcterm,
            fcunit     = self.fcunit,
        )

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [x.rh for x in self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp'))]
        self.system.subtitle('Namelist candidates')
        for nam in namcandidates:
            nam.quickview()
        return namcandidates

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        """Apply a namelist delta depending on the cycle of the binary."""
        # TODO: The mapping between the dict that contains the settings
        # (i.e elf.spawn_command_options()) and actual namelist keys should
        # be done by an extra class ... and it could be generalized to mpi
        # setup by the way !
        nam_updated = False
        # For cy41 onward, replace some namelist macros with the command line
        # arguments
        if rh.resource.cycle >= 'cy41':
            if 'NAMARG' in namcontents:
                opts_arg = self.spawn_command_options()
                logger.info('Setup macro CEXP=%s in %s', opts_arg['name'], namlocal)
                namcontents.setmacro('CEXP', opts_arg['name'])
                logger.info('Setup macro TIMESTEP=%g in %s', opts_arg['timestep'], namlocal)
                namcontents.setmacro('TIMESTEP', opts_arg['timestep'])
                fcstop = '{:s}{:d}'.format(opts_arg['fcunit'], opts_arg['fcterm'])
                logger.info('Setup macro FCSTOP=%s in %s', fcstop, namlocal)
                namcontents.setmacro('FCSTOP', fcstop)
                nam_updated = True
            else:
                logger.error('No NAMARG block in %s. It will probably crash', namlocal)

        if self.member is not None:
            namcontents.setmacro('MEMBER', self.member)
            nam_updated = True
            logger.info('Setup macro MEMBER=%s in %s', self.member, namlocal)

        return nam_updated

    def prepare_namelists(self, rh, opts=None):
        """Update each of the namelists."""
        for namrh in self.find_namelists(opts):
            namc = namrh.contents
            if self.prepare_namelist_delta(rh, namc, namrh.container.actualpath()):
                namc.rewrite(namrh.container)

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(IFSParallel, self).prepare(rh, opts)
        # Basic exports
        for optpack in ('drhook{}'.format('prof' if self.drhookprof else ''), ):
            self.export(optpack)
        self.gribapi_setup(rh, opts)
        # Namelist fixes
        self.prepare_namelists(rh, opts)
        # Fix for RTTOV coefficients
        rtcoefs = self.context.sequence.effective_inputs(role='RtCoef',
                                                         kind='rtcoef')
        if rtcoefs:
            sh = self.system
            rtpath = sh.path.dirname(sh.path.realpath(rtcoefs[0].rh.container.localpath()))
            logger.info('Setting %s = %s', 'RTTOV_COEFDIR', rtpath)
            self.env['RTTOV_COEFDIR'] = rtpath

    def execute_single(self, rh, opts):
        """Standard IFS-Like execution parallel execution."""
        self.system.ls(output='dirlst')
        super(IFSParallel, self).execute_single(rh, opts)
