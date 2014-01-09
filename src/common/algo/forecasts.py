#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.autolog import logdefault as logger

from ifsroot import IFSParallel


class Forecast(IFSParallel):
    """Forecast for IFS-like Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'forecast', 'fc' ],
                remap = dict( forecast = 'fc' )
            ),
            xpname = dict(
                default = 'FCST'
            ),
            inline = dict(
                optional = True,
                type = bool,
                default = True,
            )
        )
    )

    def prepare(self, rh, ctx, opts):
        """Default pre-link for the initial condition file"""
        super(Forecast, self).prepare(rh, ctx, opts)
        self.setlink(ctx, initrole=('InitialCondition', 'Analysis'), initname='ICMSH{0:s}INIT'.format(self.xpname))
        for namrh in [ x.rh for x in ctx.sequence.effective_inputs(role='Namelist', kind='namelist') ]:
            try:
                namc = namrh.contents
                namc['NAMCT0'].NFPOS = int(self.inline)
                self.system.header('FullPos InLine '  + str(self.inline))
                namc.rewrite(namrh.container)
            except Exception:
                logger.critical('Could not fix NAMCT0 in %s', namrh.container.actualpath())
                raise


class LAMForecast(Forecast):
    """Forecast for IFS-like Limited Area Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'lamfc', 'lamforecast' ],
                remap = dict(
                    lamforecast = 'lamfc'
                )
            ),
            synctool = dict(
                optional = True,
                default = None,
            )
        )
    )

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            name       = (self.xpname+'xxxx')[:4].upper(),
            timescheme = self.timescheme,
            timestep   = self.timestep,
            fcterm     = self.fcterm,
            fcunit     = self.fcunit,
            model      = 'aladin',
        )

    def prepare(self, rh, ctx, opts):
        """Default pre-link for boundary conditions files."""
        super(LAMForecast, self).prepare(rh, ctx, opts)
        if self.synctool:
            self.system.cp(self.synctool, 'atcp.alad')
            self.system.chmod('atcp.alad', 0755)
        cplrh = [ x.rh for x in ctx.sequence.effective_inputs(role='BoundaryConditions', kind='boundary') ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        i = 0
        for l in [ x.container.localpath() for x in cplrh ]:
            self.system.softlink(l, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, i))
            i=i+1


class DFIForecast(LAMForecast):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fcdfi' ],
            ),
        )
    )

    def prepare(self, rh, ctx, opts):
        """Pre-link boundary conditions as special DFI files."""
        super(DFIForecast, self).prepare(rh, ctx, opts)
        initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        for pseudoterm in (999, 0, 1):
            self.system.softlink(initname, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, pseudoterm))


class FullPos(IFSParallel):
    """Post-processing for IFS-like Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fullpos', 'fp' ],
                remap = dict( fullpos = 'fp' )
            ),
            xpname = dict(
                default = 'FPOS'
            ),
        )
    )

    def execute(self, rh, ctx, opts):
        """Loop on the various initial conditions provided."""
        namrh = [ x.rh for x in ctx.sequence.effective_inputs(role=('Namelist'), kind='namelistfp') ]
        namxx = [ x.rh for x in ctx.sequence.effective_inputs(role=('FullPosSelection'), kind='namselect') ]
        initrh = [ x.rh for x in ctx.sequence.effective_inputs(role=('InitialCondition', 'ModelState'), kind='historic') ]
        initrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        for r in initrh:
            self.system.title('Loop on {0:s}'.format(r.resource.term.fmthm))

            # Set a local storage place
            runstore = 'RUNOUT' + r.resource.term.fmtraw
            self.system.mkdir(runstore)

            # Define an input namelist
            try:
                namfp = [ x for x in namrh if x.resource.term == r.resource.term ].pop()
                self.system.remove('fort.4')
                self.system.symlink(namfp.container.localpath(), 'fort.4')
            except Exception:
                logger.critical('Could not get a fullpos namelist for term %s', r.resource.term)
                raise

            # Define an selection namelist
            try:
                namxt = [ x for x in namxx if x.resource.term == r.resource.term ].pop()
                self.system.remove('xxt00000000')
                self.system.symlink(namxt.container.localpath(), 'xxt00000000')
            except Exception:
                logger.critical('Could not get a selection namelist for term %s', r.resource.term)
                raise

            # Finaly set the actual init file
            self.system.remove('ICMSHFPOSINIT')
            self.system.softlink(r.container.localpath(), 'ICMSHFPOSINIT')

            # Standard execution
            super(FullPos, self).execute(rh, ctx, opts)

            # Freeze the current output
            for posfile in [ x for x in self.system.glob('PFFPOS*+*') ]:
                rootpos = re.sub('0+$', '', posfile)
                self.system.move(posfile, self.system.path.join(runstore, rootpos + r.resource.term.fmthm))
            for logfile in self.system.glob('NODE.*', 'std*'):
                self.system.move(logfile, self.system.path.join(runstore, logfile))

            # Some cleaning
            self.system.rmall('PXFPOS*', 'ncf927', 'dirlst')

    def postfix(self, rh, ctx, opts):
        """Post processing cleaning."""
        super(FullPos, self).postfix(rh, ctx, opts)
        self.system.mvglob('RUNOUT*/PFFPOS*', '.')
        self.system.cat('RUNOUT*/NODE.001_01', output='NODE.all')
        self.system.dir(output=False)
