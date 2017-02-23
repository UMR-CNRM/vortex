#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import AlgoComponentError, BlindRun
from vortex.layout.dataflow import intent
from vortex.tools import date
from .forecasts import FullPos


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
        outprefix = 'PF{0:s}AREA'.format(self.xpname)

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
                    inoutfile = outprefix + '+0000'
                    if cplpath != inoutfile:
                        sh.remove(inoutfile, fmt=cplout.rh.container.actualfmt)
                        sh.move(cplpath, inoutfile,
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
            posfile = [x for x in sh.glob(outprefix + '+*')
                       if re.match(outprefix + r'\+\d+(?:\:\d+)?(?:\.sfx)?$', x)]
            if (len(posfile) > 1):
                logger.critical('Many ' + outprefix + ' files, do not know how to adress that')
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


class CouplingLAM(Coupling):
    """Coupling for LAM to LAM Models (useless beyond cy40)."""

    _footprint = dict(
        info = "Create coupling files for a Limited Area Model (useless beyond cy40).",
        attr = dict(
            kind = dict(
                values   = ['lamcoupling'],
            ),
        )
    )

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        opts = super(CouplingLAM, self).spawn_command_options()
        opts['model'] = 'aladin'
        return opts


class Prep(BlindRun):
    """Coupling/Interpolation of Surfex files."""

    _footprint = dict(
        info = "Coupling/Interpolation of Surfex files.",
        attr = dict(
            kind = dict(
                values   = ['prep'],
            ),
            underlyingformat = dict(
                values   = ['fa', 'lfi'],
                optional = True,
                default  = 'fa'
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(Prep, self).__init__(*kargs, **kwargs)
        self._addon_checked = None

    def _check_addons(self):
        if self._addon_checked is None:
            self._addon_checked = ('sfx' in self.system.loaded_addons() and
                                   'lfi' in self.system.loaded_addons())
        if not self._addon_checked:
            raise RuntimeError("The sfx addon is needed... please load it.")

    def _do_input_format_change(self, section, output_name):
        (localpath, infmt) = (section.rh.container.localpath(),
                              section.rh.container.actualfmt)
        if section.rh.container.actualfmt != self.underlyingformat:
            if infmt == 'fa' and self.underlyingformat == 'lfi':
                if self.system.path.exists(output_name):
                    raise IOError("The %s file already exists.", output_name)
                self._check_addons()
                logger.info("Calling sfxtools' fa2lfi from %s to %s.", localpath, output_name)
                self.system.sfx_fa2lfi(localpath, output_name)
            else:
                raise RuntimeError("Format conversion from %s to %s is not possible",
                                   infmt, self.underlyingformat)
        else:
            if not self.system.path.exists(output_name):
                logger.info("Linking %s to %s", localpath, output_name)
                self.system.cp(localpath, output_name, intent=intent.IN, fmt=infmt)

    def _process_outputs(self, section, output_clim, output_name):
        (radical, outfmt) = (self.system.path.splitext(section.rh.container.localpath())[0],
                             section.rh.container.actualfmt)
        finaloutput = '{:s}_interpolated.{:s}'.format(radical, outfmt)
        finallisting = '{:s}_listing'.format(radical)
        if outfmt != self.underlyingformat:
            # There is a need for a format change
            if outfmt == 'fa' and self.underlyingformat == 'lfi':
                self._check_addons()
                logger.info("Calling lfitools' faempty from %s to %s.", output_clim, finaloutput)
                self.system.fa_empty(output_clim, finaloutput)
                logger.info("Calling sfxtools' lfi2fa from %s to %s.", output_name, finaloutput)
                self.system.sfx_lfi2fa(output_name, finaloutput)
                self.system.rm(output_name)
            else:
                raise RuntimeError("Format conversion from %s to %s is not possible",
                                   outfmt, self.underlyingformat)
        else:
            # No format change needed
            logger.info("Moving %s to %s", output_name, finaloutput)
            self.system.mv(output_name, finaloutput, fmt=outfmt)
        # Also rename the listing :-)
        self.system.mv('LISTING_PREP.txt', finallisting)
        return finaloutput

    def prepare(self, rh, opts):
        """Default pre-link for namelist file and domain change."""
        super(Prep, self).prepare(rh, opts)
        # Basic exports
        for optpack in ['drhook', 'drhook_not_mpi']:
            self.export(optpack)
        # Convert the initial clim if needed...
        iniclim = self.context.sequence.effective_inputs(role=('InitialClim',))
        if not (len(iniclim) == 1):
            raise AlgoComponentError("One Initial clim have to be provided")
        self._do_input_format_change(iniclim[0], 'PGD1.' + self.underlyingformat)
        # Convert the target clim if needed...
        targetclim = self.context.sequence.effective_inputs(role=('TargetClim',))
        if not (len(targetclim) == 1):
            raise AlgoComponentError("One Target clim have to be provided")
        self._do_input_format_change(targetclim[0], 'PGD2.' + self.underlyingformat)

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        cplsec = self.context.sequence.effective_inputs(
            role = ('InitialCondition', 'CouplingSource'),
            kind = ('historic', 'analysis')
        )
        cplsec.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        infile = 'PREP1.{:s}'.format(self.underlyingformat)
        outfile = 'PREP2.{:s}'.format(self.underlyingformat)
        targetclim = self.context.sequence.effective_inputs(role=('TargetClim',))
        targetclim = targetclim[0].rh.container.localpath()

        for sec in cplsec:
            r = sec.rh
            sh.header('Loop on {0:s}'.format(r.container.localpath()))

            # Expect the coupling source to be there...
            self.grab(sec, comment='coupling source')

            # Set the actual init file
            if sh.path.exists(infile):
                logger.critical('Cannot process input files if %s exists.', infile)
            self._do_input_format_change(sec, infile)

            # Standard execution
            super(Prep, self).execute(rh, opts)

            # Deal with outputs
            actualname = self._process_outputs(sec, targetclim, outfile)

            # promises management
            expected = [x for x in self.promises if x.rh.container.localpath() == actualname]
            if expected:
                for thispromise in expected:
                    thispromise.put(incache=True)

            # Some cleaning
            sh.rmall('*.des', fmt = r.container.actualfmt)
            sh.rmall('PREP1.*', fmt = r.container.actualfmt)
