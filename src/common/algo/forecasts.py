#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from .ifsroot import IFSParallel


class Forecast(IFSParallel):
    """Forecast for IFS-like Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = ['forecast', 'fc'],
                remap    = dict(forecast = 'fc')
            ),
            xpname = dict(
                default  = 'FCST'
            ),
            inline = dict(
                type     = bool,
                optional = True,
                default  = True,
            )
        )
    )

    @property
    def realkind(self):
        return 'forecast'

    def prepare(self, rh, opts):
        """Default pre-link for the initial condition file"""
        super(Forecast, self).prepare(rh, opts)
        self.setlink(
            initrole=('InitialCondition', 'Analysis'),
            initname='ICMSH{0:s}INIT'.format(self.xpname)
        )
        for namrh in [ x.rh for x in
                       self.context.sequence.effective_inputs(role='Namelist', kind='namelist') ]:
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
                values   = ['lamfc', 'lamforecast'],
                remap    = dict(lamforecast = 'lamfc'),
            ),
            synctool = dict(
                optional = True,
                default  = None,
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

    def prepare(self, rh, opts):
        """Default pre-link for boundary conditions files."""

        sh = self.system

        super(LAMForecast, self).prepare(rh, opts)

        if self.synctool:
            sh.cp(self.synctool, 'atcp.alad')
            sh.chmod('atcp.alad', 0755)
        cplrh = [ x.rh for x in self.context.sequence.effective_inputs(role='BoundaryConditions',
                                                                       kind='boundary') ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        i = 0
        for l in [ x.container.localpath() for x in cplrh ]:
            sh.softlink(l, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, i))
            i += 1


class DFIForecast(LAMForecast):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['fcdfi'],
            ),
        )
    )

    def prepare(self, rh, opts):
        """Pre-link boundary conditions as special DFI files."""
        super(DFIForecast, self).prepare(rh, opts)
        initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        for pseudoterm in (999, 0, 1):
            self.system.softlink(initname, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, pseudoterm))


class FullPos(IFSParallel):
    """Post-processing for IFS-like Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['fullpos', 'fp'],
                remap   = dict(fp= 'fullpos' )
            ),
            xpname = dict(
                default = 'FPOS'
            ),
        )
    )

    @property
    def realkind(self):
        return 'fullpos'

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        namrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('Namelist'), kind='namelistfp') ]
        namxx = [ x.rh for x in self.context.sequence.effective_inputs(role=('FullPosSelection'), kind='namselect') ]
        initrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('InitialCondition', 'ModelState'), kind='historic') ]
        initrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        for r in initrh:
            sh.title('Loop on {0:s}'.format(r.resource.term.fmthm))

            # Set a local storage place
            runstore = 'RUNOUT' + r.resource.term.fmtraw
            sh.mkdir(runstore)

            # Define an input namelist
            try:
                namfp = [ x for x in namrh if x.resource.term == r.resource.term ].pop()
                sh.remove('fort.4')
                sh.symlink(namfp.container.localpath(), 'fort.4')
            except Exception:
                logger.critical('Could not get a fullpos namelist for term %s', r.resource.term)
                raise

            # Define an selection namelist
            try:
                namxt = [ x for x in namxx if x.resource.term == r.resource.term ].pop()
                sh.remove('xxt00000000')
                sh.symlink(namxt.container.localpath(), 'xxt00000000')
            except Exception:
                logger.critical('Could not get a selection namelist for term %s', r.resource.term)
                raise

            # Finaly set the actual init file
            sh.remove('ICMSHFPOSINIT')
            sh.softlink(r.container.localpath(), 'ICMSHFPOSINIT')

            # Standard execution
            super(FullPos, self).execute(rh, opts)

            # Freeze the current output
            for posfile in [ x for x in sh.glob('PFFPOS*+*') ]:
                rootpos = re.sub('0+$', '', posfile)
                sh.move(
                    posfile,
                    sh.path.join(runstore, rootpos + r.resource.term.fmthm),
                    fmt = 'lfi',
                )
            for logfile in sh.glob('NODE.*', 'std*'):
                sh.move(logfile, sh.path.join(runstore, logfile))

            # Some cleaning
            sh.rmall('PXFPOS*', fmt='lfi')
            sh.ramall('ncf927', 'dirlst')

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        sh = self.system
        super(FullPos, self).postfix(rh, opts)
        for fpfile in [ x for x in sh.glob('RUNOUT*/PFFPOS*') if sh.path.isfile(x) ]:
            sh.move(fpfile, sh.path.basename(fpfile), fmt='lfi')
        sh.cat('RUNOUT*/NODE.001_01', output='NODE.all')
        sh.dir(output=False)
