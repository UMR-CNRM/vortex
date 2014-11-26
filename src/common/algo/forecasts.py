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

        sh = self.system

        analysis = self.setlink(
            initrole = ('InitialCondition', 'Analysis'),
            initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        )

        if analysis:
            analysis  = analysis.pop()
            thismonth = analysis.resource.date.month

            def checkmonth(actualrh):
                return bool(actualrh.resource.month == thismonth)

            self.setlink(
                initrole = 'GlobalClim',
                initkind = 'clim_model',
                initname = 'Const.Clim',
                inittest = checkmonth,
            )

            for bdaprh in [ x.rh for x in self.context.sequence.effective_inputs(
                role = 'LocalClim',
                kind = 'clim_bdap',
            ) if x.rh.resource.month == thismonth ]:
                thisclim = bdaprh.container.localpath()
                thisname = 'const.clim.' + bdaprh.resource.geometry.area
                if thisclim != thisname:
                    sh.symlink(thisclim, thisname)

            # At least, expect the analysis to be there...
            self.wait_and_get(analysis, comment='analysis')

        for namrh in [ x.rh for x in self.context.sequence.effective_inputs(
            role = 'Namelist',
            kind = 'namelist',
        ) ]:
            try:
                namc = namrh.contents
                namc['NAMCT0'].NFPOS = int(self.inline)
                sh.header('FullPos InLine '  + str(self.inline))
                namc.rewrite(namrh.container)
            except Exception:
                logger.critical('Could not fix NAMCT0 in %s', namrh.container.actualpath())
                raise

        # Promises should be nicely managed by a co-proccess
        if self.promises:
            self.flyput = True
            self.io_poll_args = ('ICMSH', 'PF')


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
                default  = 'atcp.alad',
            ),
            synctpl = dict(
                optional = True,
                default  = 'sync.fetch.tpl',
            ),
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
        super(LAMForecast, self).prepare(rh, opts)

        sh = self.system

        # Check boundaries conditions
        cplrh = [ x.rh for x in self.context.sequence.effective_inputs(
            role = 'BoundaryConditions',
            kind = 'boundary'
        ) ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        # Ordered pre-linking of boundaring and building ot the synchronization tools
        firstsync = None
        sh.header('Check boundaries...')
        if any([ x.is_expected() for x in cplrh ]):
            logger.info('Some boundaries conditions are still expected')
            self.mksync = True
        else:
            logger.info('All boundaries conditions available')
            self.mksync = False

        for i, bound in enumerate(cplrh):
            thisbound = bound.container.localpath()
            sh.softlink(thisbound, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, i))
            if self.mksync:
                thistool = self.synctool + '.{0:03d}'.format(i)
                bound.mkgetpr(prgetter=thistool, tplfetch=self.synctpl)
                if firstsync is None:
                    firstsync = thistool

        # Set up the first synchronization step
        if firstsync is not None:
            sh.symlink(firstsync, self.synctool)

    def postfix(self, rh, opts):
        """Post forecast information and cleaning."""
        sh = self.system
        super(LAMForecast, self).postfix(rh, opts)
        if self.mksync:
            synclog = self.synctool + '.log'
            if sh.path.exists(synclog):
                sh.subtitle(synclog)
                sh.cat(synclog, output=False)


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

        namrh = [ x.rh for x in self.context.sequence.effective_inputs(
            role = 'Namelist',
            kind = 'namelistfp'
        ) ]

        namxx = [ x.rh for x in self.context.sequence.effective_inputs(
            role = 'FullPosSelection',
            kind = 'namselect',
        ) ]

        initrh = [ x.rh for x in self.context.sequence.effective_inputs(
            role = ('InitialCondition', 'ModelState'),
            kind = 'historic',
        ) ]
        initrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        for r in initrh:
            sh.subtitle('Loop on {0:s}'.format(r.resource.term.fmthm))

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
