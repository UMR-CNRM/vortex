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
        info = "Create coupling files for a Limited Area Model.",
        attr = dict(
            kind = dict(
                values   = ['coupling'],
            ),
            basedate = dict(
                info     = "The run date of the coupling generating process",
                type     = date.Date,
            ),
            server_run = dict(
                values   = [True, False],
            ),
            serversync_method = dict(
                default  = 'simple_socket',
            ),
            serversync_medium = dict(
                default  = 'cnt3_wait',
            )
        )
    )

    @property
    def realkind(self):
        return 'coupling'

    def prepare(self, rh, opts):
        """Default pre-link for namelist file and domain change."""
        super(Coupling, self).prepare(rh, opts)
        namsec = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
        for nam in [x.rh for x in namsec if 'NAMFPC' in x.rh.contents]:
            logger.info('Substitute "AREA" to CFPDOM namelist entry')
            nam.contents['NAMFPC']['CFPDOM(1)'] = 'AREA'
            nam.save()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

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

        cplsurf = self.context.sequence.effective_inputs(role = ('SurfaceInitialCondition',
                                                                 'SurfaceCouplingSource'))
        cplsurf.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        surfacing = bool(cplsurf)
        infilesurf = 'ICMSH{0:s}INIT.sfx'.format(self.xpname)
        if surfacing:
            # Link in the Surfex's PGD
            self.setlink(
                initrole = ('ClimPGD', ),
                initkind = ('pgdfa', 'pgdlfi'),
                initname = 'const.clim.sfx.AREA',
            )

        for sec in cplsec:
            r = sec.rh
            sh.subtitle('Loop on {0:s}'.format(str(r.resource)))

            # First attempt to set actual date as the one of the source model
            actualdate = r.resource.date + r.resource.term

            # Expect the coupling source to be there...
            self.grab(sec, comment='coupling source')

            # Set the actual init file
            if sh.path.exists(infile):
                if isMany:
                    logger.critical('Cannot process multiple Historic files if %s exists.', infile)
            else:
                sh.cp(r.container.localpath(), infile, fmt=r.container.actualfmt, intent=intent.IN)

            # If the surface file is needed, set the actual initsurf file
            if cplsurf:
                # Expecting the coupling surface source to be there...
                cplsurf_in  = cplsurf.pop(0)
                self.grab(cplsurf_in, comment='coupling surface source')
                if sh.path.exists(infilesurf):
                    if isMany:
                        logger.critical('Cannot process multiple surface historic files if %s exists.', infilesurf)
                else:
                    sh.cp(cplsurf_in.rh.container.localpath(), infilesurf,
                          fmt=cplsurf_in.rh.container.actualfmt, intent=intent.IN)
            elif surfacing:
                logger.error('No more surface source to loop on for coupling')

            # The output could be an input as well
            if cplguess:
                cplout  = cplguess.pop(0)
                cplpath = cplout.rh.container.localpath()
                if sh.path.exists(cplpath):
                    actualdateguess = cplout.rh.resource.date + cplout.rh.resource.term
                    if (actualdate == actualdateguess):
                        logger.error('The guess date, %s, is different from the source date %s, !',
                                     actualdateguess.reallynice(), actualdate.reallynice())
                    # Expect the coupling guess to be there...
                    self.grab(cplout, comment='coupling guess')
                    logger.info('Coupling with existing guess <%s>', cplpath)
                    if cplpath != 'PFFPOSAREA+0000':
                        sh.remove('PFFPOSAREA+0000', fmt=cplout.rh.container.actualfmt)
                        sh.move(cplpath, 'PFFPOSAREA+0000',
                                fmt=cplout.rh.container.actualfmt,
                                intent=intent.INOUT)
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
            posfile = [x for x in sh.glob('PFFPOSAREA+*')
                       if re.match(r'PFFPOSAREA\+\d+(?:\:\d+)?(?:\.sfx)?$', x)]
            if (len(posfile) > 1):
                logger.critical('Many PFFPOSAREA files, do not know how to adress that')
            posfile = posfile[0]
            actualterm = (actualdate - self.basedate).time()
            actualname = (re.sub(r'^.+?((?:_\d+)?)(?:\+[:\d]+)?$', r'CPLOUT\1+', r.container.localpath()) +
                          actualterm.fmthm)
            if isMany:
                sh.move(sh.path.realpath(posfile), actualname,
                        fmt=r.container.actualfmt)
                if sh.path.exists(posfile):
                    sh.rm(posfile)
            else:
                # This is here because of legacy with .sfx files
                sh.cp(sh.path.realpath(posfile), actualname,
                      fmt=r.container.actualfmt, intent=intent.IN)

            # promises management
            expected = [x for x in self.promises if x.rh.container.localpath() == actualname]
            if expected:
                for thispromise in expected:
                    thispromise.put(incache=True)

            # The only one listing
            if not self.server_run:
                sh.cat('NODE.001_01', output='NODE.all')

            # prepares the next execution
            if isMany:
                # Some cleaning
                sh.rmall('PXFPOS*', fmt = r.container.actualfmt)
                sh.remove(infile, fmt = r.container.actualfmt)
                if cplsurf:
                    sh.remove(infilesurf, fmt = r.container.actualfmt)
                if not self.server_run:
                    sh.rmall('ncf927', 'dirlst', 'NODE.[0123456789]*', 'std*')

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        super(Coupling, self).postfix(rh, opts)
        self.system.dir(output=False)
