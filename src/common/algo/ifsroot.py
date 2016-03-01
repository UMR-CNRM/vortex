#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import Parallel


class IFSParallel(Parallel):
    """Abstract IFSModel parallel algo components."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            kind = dict(
                default  = 'ifsrun',
            ),
            conf = dict(
                type     = int,
                optional = True,
                default  = 1,
            ),
            timescheme = dict(
                optional = True,
                default  = 'sli',
                values   = ['eul', 'eulerian', 'sli', 'semilag'],
                remap = dict(
                    eulerian = 'eul',
                    semilag  = 'sli'
                )
            ),
            timestep = dict(
                type     = float,
                optional = True,
                default  = 600.,
            ),
            fcterm = dict(
                type = int,
                optional = True,
                default = 0,
            ),
            fcunit = dict(
                optional = True,
                default  = 'h',
                values   = ['h', 'hour', 't', 'step'],
                remap = dict(
                    hour = 'h',
                    step = 't'
                )
            ),
            xpname = dict(
                optional = True,
                default  = 'XPVT'
            ),
            drhookprof = dict(
                optional = True,
                type     = bool,
                default  = False,
            ),
            member = dict(
                optional = True,
                type     = int,
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
        namcandidates = [ x.rh for x in self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp')) ]
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
        for optpack in ('drhook{}'.format('prof' if self.drhookprof else ''), 
                        'gribapi'):
            self.export(optpack)
        self.prepare_namelists(rh, opts)

    def execute(self, rh, opts):
        """Standard IFS-Like execution parallel execution."""
        self.system.ls(output='dirlst')
        super(IFSParallel, self).execute(rh, opts)
