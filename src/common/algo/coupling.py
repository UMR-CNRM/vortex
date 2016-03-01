#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools import date
from .forecasts import FullPos
from vortex.layout.dataflow import intent


class Coupling(FullPos):
    """Coupling for IFS-like LAM Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = [ 'coupling' ],
            ),
            basedate = dict(
                type     = date.Date,
                optional = True,
            ),

        )
    )

    @property
    def realkind(self):
        return 'coupling'

    def prepare(self, rh, opts):
        """Default pre-link for namelist file and domain change."""
        super(Coupling, self).prepare(rh, opts)
        namsec = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
        for nam in [ x.rh for x in namsec if 'NAMFPC' in x.rh.contents ]:
            logger.info('Substitute "AREA" to CFPDOM namelist entry')
            nam.contents['NAMFPC']['CFPDOM(1)'] = 'AREA'
            nam.save()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system
        basedate = self.basedate or self.env.YYYYMMDDHH

        cplsec = self.context.sequence.effective_inputs(
            role = ('InitialCondition', 'CouplingSource'),
            kind = ('historic', 'analysis')
        )
        cplsec.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        infile = 'ICMSH{0:s}INIT'.format(self.xpname)
        isMany = len(cplsec) > 1

        cplguess = self.context.sequence.effective_inputs(role = 'Guess')
        cplguess.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        guessing = bool(cplguess)

        cplsurf = self.context.sequence.effective_inputs(role = ('SurfaceInitialCondition', 'SurfaceCouplingSource'))
        cplsurf.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        surfacing = bool(cplsurf)
        infilesurf = 'ICMSH{0:s}INIT.sfx'.format(self.xpname)

        for sec in cplsec:
            r = sec.rh
            sh.subtitle('Loop on {0:s}'.format(str(r.resource)))

            # First attempt to set actual date as the one of the source model
            actualdate = r.resource.date + r.resource.term

            # Set the actual init file
            if sh.path.exists(infile):
                if isMany:
                    logger.critical('Cannot process multiple Historic files if %s exists.', infile)
            else:
                sh.cp(r.container.localpath(), infile, fmt=r.container.actualfmt, intent=intent.IN)

            # If the surface file is needed, set the actual initsurf file
            if cplsurf:
                cplout  = cplsurf.pop(0)
                if sh.path.exists(infilesurf):
                    if isMany:
                        logger.critical('Cannot process multiple surface historic files if %s exists.', infilesurf)
                else:
                    sh.cp(cplout.rh.container.localpath(), infilesurf, fmt=cplout.rh.container.actualfmt, intent=intent.IN)
            elif surfacing:
                logger.error('No more surface source to loop on for coupling')

            # Expect the coupling source to be there...
            self.grab(sec, comment='coupling source')

            # The output could be an input as well
            if cplguess:
                cplout  = cplguess.pop(0)
                cplpath = cplout.rh.container.localpath()
                if sh.path.exists(cplpath):
                    actualdateguess = cplout.rh.resource.date + cplout.rh.resource.term
                    if (actualdate == actualdateguess):
                        logger.error('The guess date, {:s}, is different from the source date {:s}, !'
                                     .format(actualdateguess.reallynice(), actualdate.reallynice()))
                    # Expect the coupling guess to be there...
                    self.grab(cplout, comment='coupling guess')
                    logger.info('Coupling with existing guess <%s>', cplpath)
                    if cplpath != 'PFFPOSAREA+0000':
                        sh.remove('PFFPOSAREA+0000', fmt='lfi')
                        sh.softlink(cplpath, 'PFFPOSAREA+0000')
                else:
                    logger.warning('Missing guess input for coupling <%s>', cplpath)
            elif guessing:
                logger.error('No more guess to loop on for coupling')

            # Find out actual monthly climatological resource
            actualmonth = date.Month(actualdate)

            def checkmonth(actualrh):
                return bool(actualrh.resource.month == actualmonth)

            sh.remove('Const.Clim')
            self.setlink(
                initrole = ('GlobalClim', 'InitialClim'),
                initkind = 'clim_model',
                initname = 'Const.Clim',
                inittest = checkmonth
            )

            sh.remove('const.clim.AREA')
            self.setlink(
                initrole = ('LocalClim', 'TargetClim'),
                initkind = 'clim_model',
                initname = 'const.clim.AREA',
                inittest = checkmonth
            )

            # Standard execution
            super(Coupling, self).execute(rh, opts)

            # Set a local appropriate file
            posfile = [ x for x in sh.glob('PFFPOSAREA+*') if re.match(r'PFFPOSAREA\+\d+(?:\:\d+)?(?:\.sfx)?$', x) ]
            if (len(posfile) > 1):
                logger.critical('Many PFFPOSAREA files, do not know how to adress that')
            posfile = posfile[0]
            actualterm = (actualdate - basedate).time()

            actualname = re.sub(r'^.+?((?:_\d+)?)\+[:\w]+$', r'CPLOUT\1+', r.container.localpath()) + actualterm.fmthm
            sh.move(
                    sh.path.realpath(posfile),
                    actualname,
                    fmt=r.container.actualfmt
            )
            if sh.path.exists(posfile):
                sh.rm(posfile)
            
            # promises management
            expected = [ x for x in self.promises if x.rh.container.localpath() == actualname ]
            if expected:
                for thispromise in expected:
                    thispromise.put(incache=True)

            # prepares the next execution
            if isMany:
                # The only one listing
                sh.cat('NODE.001_01', output='NODE.all')

                # Some cleaning
                sh.rmall('PXFPOS*', fmt = r.container.actualfmt)
                sh.rmall('ncf927', 'dirlst')
                sh.remove(infile, fmt = r.container.actualfmt)
                if cplsurf:
                    sh.remove(infilesurf, fmt = r.container.actualfmt)

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        super(Coupling, self).postfix(rh, opts)
        sh = self.system
        if sh.path.exists('NODE.all'):
            sh.move('NODE.all', 'NODE.001_01')
        sh.dir(output=False)

