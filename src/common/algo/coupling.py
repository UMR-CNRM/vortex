#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools import date
from .ifsroot import IFSParallel


class Coupling(IFSParallel):
    """Coupling for IFS-like LAM Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = [ 'coupling' ],
            ),
            xpname = dict(
                default  = 'FPOS'
            ),
            conf = dict(
                default  = 1,
            ),
            basedate = dict(
                type     = date.Date,
                optional = True,
                default  = None,
            )
        )
    )

    @property
    def realkind(self):
        return 'coupling'

    def prepare(self, rh, opts):
        """Default pre-link for climatological files"""
        super(Coupling, self).prepare(rh, opts)
        namrh = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
        for nam in [ x for x in namrh if 'NAMFPC' in x.contents ]:
            logger.info('Substitute "AREA" to CFPDOM namelist entry')
            nam.contents['NAMFPC']['CFPDOM'] = 'AREA'
            nam.save()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        cplrh = [ x.rh for x in self.context.sequence.effective_inputs(
            role = ('InitialCondition', 'CouplingSource'),
            kind = ('historic', 'analysis')
        ) ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        cplguess = [ x.rh for x in self.context.sequence.effective_inputs(role = 'Guess') ]
        cplguess.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        guessing = bool(cplguess)

        basedate = self.basedate or self.env.YYYYMMDDHH

        for r in cplrh:
            sh.title('Loop on {0:s}'.format(str(r.resource)))

            # Set a local storage place
            runstore = 'RUNOUT' + r.resource.term.fmtraw
            sh.mkdir(runstore)

            # Find out actual monthly climatological resource
            actualdate  = r.resource.date + r.resource.term
            actualmonth = date.Month(actualdate)

            def checkmonth(actualrh):
                return bool(actualrh.resource.month == actualmonth)

            sh.remove('Const.Clim')
            self.setlink(
                initrole = 'GlobalClim',
                initkind = 'clim_model',
                initname = 'Const.Clim',
                inittest = checkmonth
            )

            sh.remove('const.clim.AREA')
            self.setlink(
                initrole = 'LocalClim',
                initkind = 'clim_model',
                initname = 'const.clim.AREA',
                inittest = checkmonth
            )

            # Finaly set the actual init file
            sh.rm('ICMSHFPOSINIT')
            sh.softlink(r.container.localpath(), 'ICMSHFPOSINIT')

            # Expected output
            if cplguess:
                cplout  = cplguess.pop(0)
                cplpath = cplout.container.localpath()
                actualdate = cplout.resource.date + cplout.resource.term
                if sh.path.exists(cplpath):
                    logger.info('Coupling with existing guess <%s>', cplpath)
                    if cplpath != 'PFFPOSAREA+0000':
                        sh.remove('PFFPOSAREA+0000', fmt='lfi')
                        sh.softlink(cplpath, 'PFFPOSAREA+0000')
                else:
                    logger.warning('Missing guess input for coupling <%s>', cplpath)
            elif guessing:
                logger.error('No more guess to loop on for coupling')

            # Standard execution
            super(Coupling, self).execute(rh, opts)

            # Freeze the current output
            for posfile in [ x for x in sh.glob('PFFPOSAREA+*') if re.match(r'PFFPOSAREA\+\d+(?:\:\d+)?$', x) ]:
                actualterm = (actualdate - basedate).time() 
                sh.mv(
                    sh.path.realpath(posfile),
                    sh.path.join(runstore, 'CPLOUT+' + actualterm.fmthm),
                    fmt='lfi',
                )
                if sh.path.exists(posfile):
                    sh.rm(posfile)
            for logfile in sh.glob('NODE.*', 'std*'):
                sh.move(logfile, sh.path.join(runstore, logfile))

            # Some cleaning
            sh.rmall('PXFPOS*', fmt='lfi')
            sh.rmall('ncf927', 'dirlst')

    def postfix(self, rh, opts):
        """Post coupling cleaning."""
        super(Coupling, self).postfix(rh, opts)

        sh = self.system

        for cplfile in sh.glob('RUNOUT*/CPLOUT+*:[0-9][0-9]'):
            sh.move(cplfile, sh.path.basename(cplfile), fmt='lfi')
        sh.cat('RUNOUT*/NODE.001_01', output='NODE.all')
        sh.dir(output=False)

