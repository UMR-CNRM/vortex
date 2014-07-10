#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.autolog import logdefault as logger

from vortex.algo.components import BlindRun


class Fa2Grib(BlindRun):
    """Standard FA conversion, e.g. with PROGRID as a binary resource."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fa2grib' ],
            ),
            fortnam = dict(
                optional = True,
                default = 'fort.4',
            ),
            fortinput = dict(
                optional = True,
                default = 'fort.11',
            ),
            compact = dict(
                optional = True,
                default = 'L'
            ),
            timeshift = dict(
                optional = True,
                type = int,
                default = 0,
            ),
            numod = dict(
                optional = True,
                type = int,
                default = 221,
            ),
            sciz = dict(
                optional = True,
                type = int,
                default = 0,
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
        self.compact    = self.env.get('VORTEX_GRIB_COMPACT', 'L')
        self.timeshift  = self.env.get('VORTEX_GRIB_SHIFT', False)
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
            nb['CLFSORT(1)'] = thisoutput
            nb['CDNOMF(1)'] = self.fortinput
            with open(self.fortnam, 'w') as namfd:
                namfd.write(nb.dumps())
            self.system.header('{0:s} : local namelist {1:s} dump'.format(self.realkind, self.fortnam))
            self.system.cat(self.fortnam, output=False)

            # Finaly set the actual init file
            self.system.softlink(r.container.localpath(), self.fortinput)

            # Standard execution
            opts['loop'] = r.resource.term
            super(Fa2Grib, self).execute(rh, opts)

            # Freeze the current output
            if self.system.path.exists(thisoutput):
                self.system.move(thisoutput, 'GRIB{0:s}+{1:s}'.format(r.resource.geometry.area, r.resource.term.fmthm))
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
        self.system.remove(self.fortnam)
