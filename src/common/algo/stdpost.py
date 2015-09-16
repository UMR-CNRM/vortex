#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import BlindRun
from vortex.syntax.stdattrs import DelayedEnvValue


class Fa2Grib(BlindRun):
    """Standard FA conversion, e.g. with PROGRID as a binary resource."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fa2grib' ],
            ),
            timeout = dict(
                default = 180,
            ),
            fortnam = dict(
                optional = True,
                default  = 'fort.4',
            ),
            fortinput = dict(
                optional = True,
                default  = 'fort.11',
            ),
            compact = dict(
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_COMPACT', 'L'),
            ),
            timeshift = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_SHIFT', 0),
            ),
            timeunit = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_TUNIT', 1),
            ),
            numod = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_NUMOD', 221),
            ),
            sciz = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_SCIZ', 0),
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Fa2Grib, self).prepare(rh, opts)
        self.system.remove(self.fortinput)
        self.env.DR_HOOK_NOT_MPI = 1

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        gprh = [ x.rh for x in self.context.sequence.effective_inputs(role='Gridpoint', kind='gridpoint') ]
        gprh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        thisoutput = 'GRIDOUTPUT'

        for r in gprh:
            self.system.title('Loop on domain {0:s} and term {1:s}'.format(
                r.resource.geometry.area, r.resource.term.fmthm))

            # Some preventive cleaning
            self.system.remove(thisoutput)
            self.system.remove(self.fortnam)

            # Build the local namelist block
            from vortex.tools.fortran import NamelistBlock
            nb = NamelistBlock(name='NAML')
            nb.NBDOM = 1
            nb.CHOPER = self.compact
            nb.INUMOD = self.numod

            if self.sciz:
                nb.ISCIZ = self.sciz

            if self.timeshift:
                nb.IHCTPI = self.timeshift

            if self.timeunit:
                nb.ITUNIT = self.timeunit

            nb['CLFSORT(1)'] = thisoutput
            nb['CDNOMF(1)'] = self.fortinput
            with open(self.fortnam, 'w') as namfd:
                namfd.write(nb.dumps())

            self.system.header('{0:s} : local namelist {1:s} dump'.format(self.realkind, self.fortnam))
            self.system.cat(self.fortnam, output=False)

            # Expect the input FP file source to be there...
            self.grab(r, comment='fullpos source')

            # Finaly set the actual init file
            self.system.softlink(r.container.localpath(), self.fortinput)

            # Standard execution
            opts['loop'] = r.resource.term
            super(Fa2Grib, self).execute(rh, opts)

            # Freeze the current output
            if self.system.path.exists(thisoutput):
                actualname = 'GRIB{0:s}+{1:s}'.format(r.resource.geometry.area, r.resource.term.fmthm)
                self.system.move(thisoutput, actualname)
                expected = [ x for x in self.promises if x.container.localpath() == actualname ]
                for thispromise in expected:
                    thispromise.put(incache=True)
            else:
                logger.warning('Missing some grib output for domain %s term %s',
                               r.resource.geometry.area, r.resource.term.fmthm)

            # Some cleaning
            self.system.rmall('DAPDIR', self.fortinput)


class AddField(BlindRun):
    """Miscellaneous manipulation on input FA resources."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'addcst', 'addconst', 'addfield' ],
                remap = dict(
                    addconst = 'addcst',
                ),
            ),
            fortnam = dict(
                optional = True,
                default = 'fort.4',
            ),
            fortinput = dict(
                optional = True,
                default = 'fort.11',
            ),
            fortoutput = dict(
                optional = True,
                default = 'fort.12',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(AddField, self).prepare(rh, opts)
        self.system.remove(self.fortinput)
        self.env.DR_HOOK_NOT_MPI = 1

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        # Is there any namelist provided ?
        namrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('Namelist'), kind='namelist') ]
        if namrh:
            self.system.softlink(namrh[0].container.localpath(), self.fortnam)
        else:
            logger.warning('Do not find any namelist for %s', self.kind)

        # Look for some sources files
        srcrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('Gridpoint', 'Sources'),
                                                                       kind='gridpoint') ]
        srcrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        for r in srcrh:
            self.system.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                           r.resource.term.fmthm))

            # Some cleaning
            self.system.remove(self.fortinput)
            self.system.remove(self.fortoutput)

            # Prepare double input
            self.system.link(r.container.localpath(), self.fortinput)
            self.system.cp(r.container.localpath(), self.fortoutput)

            # Standard execution
            opts['loop'] = r.resource.term
            super(AddField, self).execute(rh, opts)

            # Some cleaning
            self.system.rmall('DAPDIR', self.fortinput, self.fortoutput)

    def postfix(self, rh, opts):
        """Post add cleaning."""
        super(AddField, self).postfix(rh, opts)
        self.system.remove(self.fortnam)


class DiagPI(BlindRun):
    """Execution of diagnotics on grib input (Arome-PI's specific)."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'diagpi' ],
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(DiagPI, self).prepare(rh, opts)
        # Prevent DrHook to initialise MPI and setup grib_api
        for optpack in ('drhook_not_mpi', 'gribapi'):
            self.export(optpack)

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super(DiagPI, self).spawn_hook()
        if self.system.path.exists('fort.4'):
            self.system.subtitle('{0:s} : dump namelist <fort.4>'.format(self.realkind))
            self.system.cat('fort.4', output=False)

    def execute(self, rh, opts):
        """Loop on the various grib files provided."""
        srcrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('Gridpoint', 'Sources'),
                                                                       kind='gridpoint') ]
        srcrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        for r in srcrh:
            self.system.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                           r.resource.term.fmthm))
            # Tweak the namelist
            namrh = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
            for nam in [ x for x in namrh if 'NAM_PARAM' in x.contents ]:
                logger.info("Substitute the date (%s) to AAAAMMJJHH namelist entry", r.resource.date.ymdh)
                nam.contents['NAM_PARAM']['AAAAMMJJHH'] = r.resource.date.ymdh
                logger.info("Substitute the the number of terms to NECH(0) namelist entry")
                nam.contents['NAM_PARAM']['NECH(0)'] = 1
                logger.info("Substitute the ressource term to NECH(1) namelist entry")
                # NB: term should be expressed in minutes
                nam.contents['NAM_PARAM']['NECH(1)'] = int(r.resource.term)
                nam.save()

            # Expect the input grib file to be here
            self.grab(r, comment='diagpi source')
            # Also link in previous grib files in order to compute some winter diagnostics
            srcprh = [x.rh
                      for x in self.context.sequence.effective_inputs(role=('Preview', 'Previous'),
                                                                      kind='gridpoint')
                      if x.rh.resource.term < r.resource.term]
            for pr in srcprh:
                self.grab(pr, comment='diagpi additional source for winter diag')

            # Standard execution
            opts['loop'] = r.resource.term
            super(DiagPI, self).execute(rh, opts)
