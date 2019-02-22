#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import re

from bronx.fancies import loggers
from bronx.stdtypes import date

from common.algo.ifsroot import IFSParallel
from common.tools.drhook import DrHookDecoMixin
from vortex.algo.components import AlgoComponentError, BlindRun
from vortex.layout.dataflow import intent

from .forecasts import FullPos

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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
                optional = True
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
        cplsec.sort(key=lambda s: s.rh.resource.term)
        ininc = self.naming_convention('ic', rh)
        infile = ininc()
        isMany = len(cplsec) > 1
        outprefix = 'PF{0:s}AREA'.format(self.xpname)

        cplguess = self.context.sequence.effective_inputs(role = 'Guess')
        cplguess.sort(key=lambda s: s.rh.resource.term)
        guessing = bool(cplguess)

        cplsurf = self.context.sequence.effective_inputs(role = ('SurfaceInitialCondition',
                                                                 'SurfaceCouplingSource'))
        cplsurf.sort(key=lambda s: s.rh.resource.term)
        surfacing = bool(cplsurf)
        inisurfnc = self.naming_convention('ic', rh, model='surfex')
        infilesurf = inisurfnc()
        if surfacing:
            # Link in the Surfex's PGD
            sclimnc = self.naming_convention(kind='targetclim', rh=rh, model='surfex')
            self.setlink(
                initrole = ('ClimPGD', ),
                initkind = ('pgdfa', 'pgdlfi'),
                initname = sclimnc(area='AREA')
            )

        for sec in cplsec:
            r = sec.rh
            sh.subtitle('Loop on {0!s}'.format(r.resource))

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
            self.climfile_fixer(rh, convkind='modelclim', month=actualmonth,
                                inputrole=('GlobalClim', 'InitialClim'),
                                inputkind='clim_model')
            self.climfile_fixer(rh, convkind='targetclim', month=actualmonth,
                                inputrole=('LocalClim', 'TargetClim'),
                                inputkind='clim_model', area='AREA')

            # Standard execution
            super(Coupling, self).execute(rh, opts)

            # Set a local appropriate file
            posfile = [x for x in sh.glob(outprefix + '+*')
                       if re.match(outprefix + r'\+\d+(?:\:\d+)?(?:\.sfx)?$', x)]
            if (len(posfile) > 1):
                logger.critical('Many ' + outprefix + ' files, do not know how to adress that')
            posfile = posfile[0]
            if self.basedate is None:
                actualterm = r.resource.term
            else:
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


class Prep(BlindRun, DrHookDecoMixin):
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
        self.system.subtitle("Processing inputs")
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
        self.system.subtitle("Processing outputs")
        if outfmt != self.underlyingformat:
            # There is a need for a format change
            if outfmt == 'fa' and self.underlyingformat == 'lfi':
                self._check_addons()
                logger.info("Calling lfitools' faempty from %s to %s.", output_clim, finaloutput)
                self.system.fa_empty(output_clim, finaloutput)
                logger.info("Calling sfxtools' lfi2fa from %s to %s.", output_name, finaloutput)
                self.system.sfx_lfi2fa(output_name, finaloutput)
                finallfi = '{:s}_interpolated.{:s}'.format(radical, self.underlyingformat)
                self.system.mv(output_name, finallfi)
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
        cplsec.sort(key=lambda s: s.rh.resource.term)
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
            sh.subtitle("Listing after PREP")
            sh.dir(output=False, fatal=False)

            # Deal with outputs
            actualname = self._process_outputs(sec, targetclim, outfile)

            # promises management
            expected = [x for x in self.promises if x.rh.container.localpath() == actualname]
            if expected:
                for thispromise in expected:
                    thispromise.put(incache=True)

            # Some cleaning
            sh.rmall('*.des')
            sh.rmall('PREP1.*')


class C901(IFSParallel):
    """Run of C931 configuration"""

    _footprint = dict(
        info = "Run C901 configuration",
        attr = dict(
            kind = dict(
                values = ["c901", ]
            ),
            clim = dict(
                type = bool
            ),
            xpname = dict(
                default = 'a001'
            )
        )
    )

    SPECTRAL_FILE_SH = "ICMSH{prefix}INIT{suffix}"
    GRIDPOINT_FILE_UA = "ICMUA{prefix}INIT{suffix}"
    GRIDPOINT_FILE_GG = "ICMGG{prefix}INIT{suffix}"
    OUTPUT_FILE_NAME = "CN90x{}INIT"
    OUTPUT_LISTING_NAME = "NODE.001_01"
    LIST_INPUT_FILES = [("SpectralFileSH", SPECTRAL_FILE_SH),
                        ("GridpointFileUA", GRIDPOINT_FILE_UA),
                        ("GridpointFileGG", GRIDPOINT_FILE_GG)]
    LIST_CST_INPUT_FILES = [("ConstantSpectralFileSH", SPECTRAL_FILE_SH),
                            ("ConstantGridpointFileUA", GRIDPOINT_FILE_UA),
                            ("ConstantGrdipointFileGG", GRIDPOINT_FILE_GG)]

    @property
    def realkind(self):
        return "c901"

    def sort_files_per_prefix(self, list_types, unique=False):
        """Function used to sort the files according to their prefix in a given type"""
        result = dict()
        for (file_role, file_template) in list_types:
            result[file_role] = dict()
            input_files = self.context.sequence.effective_inputs(
                role = file_role
            )
            template = file_template.format(prefix=r"(?P<prefix>\S{4})", suffix=r"(?P<suffix>\S*)")
            for file_s in input_files:
                file_name = file_s.rh.container.filename
                find_elements = re.search(template, file_name)
                if find_elements is None:
                    logger.error("The name of the file %s do not follow the template %s.", file_name, template)
                    raise ValueError("The name of the file do not follow the template.")
                else:
                    if find_elements.group("prefix") not in result[file_role]:
                        result[file_role][find_elements.group("prefix")] = list()
                    else:
                        if unique:
                            logger.error("Only one file should be present for each type and each suffix.")
                            raise ValueError("Only one file should be present for each suffix.")
                    result[file_role][find_elements.group("prefix")].append(file_s)
            if result[file_role]:
                for file_prefix in result[file_role]:
                    result[file_role][file_prefix].sort(key=lambda s: s.rh.resource.date + s.rh.resource.term)
            else:
                del result[file_role]
        return result

    def execute(self, rh, opts):
        """Loop on the various files provided"""

        sh = self.system

        # Create the template for files to be removed at each validity date and for the outputname
        deleted_spectral_file_SH = self.SPECTRAL_FILE_SH.format(prefix="*", suffix="")
        deleted_gridpoint_file_UA = self.GRIDPOINT_FILE_UA.format(prefix="*", suffix="")
        deleted_gridpoint_file_GG = self.GRIDPOINT_FILE_GG.format(prefix="*", suffix="")
        output_name = self.OUTPUT_FILE_NAME.format(self.xpname.upper())

        # Sort input files
        sorted_cst_input_files = self.sort_files_per_prefix(self.LIST_CST_INPUT_FILES, unique=True)
        sorted_input_files = self.sort_files_per_prefix(self.LIST_INPUT_FILES)

        # Determine the validity present for each non constant input files, check that they are the same for all
        # Also create the list of the filenames that should be deleted
        input_validity = list()
        for file_role in sorted_input_files:
            for file_prefix in sorted_input_files[file_role]:
                input_validity.append([s.rh.resource.date + s.rh.resource.term
                                       for s in sorted_input_files[file_role][file_prefix]])
        test_wrong_input_validity = True
        for i in range(1, len(input_validity)):
            test_wrong_input_validity = test_wrong_input_validity and (input_validity[0] == input_validity[i])
        self.algoassert(test_wrong_input_validity, "The files of each type must have the same validity dates.")

        # Modify namelist
        input_namelist = self.context.sequence.effective_inputs(
            role = "Namelist",
            kind = "namelist"
        )
        for namelist in input_namelist:
            namcontents = namelist.rh.contents
            logger.info('Setup macro LLCLIM=%s in %s', self.clim, namelist.rh.container.actualpath())
            namcontents.setmacro('LLCLIM', self.clim)
            namcontents.rewrite(namelist.rh.container)

        for current_validity in input_validity[0]:
            # Deal with constant input files (gridpoint and spectral)
            for (file_role, file_template) in self.LIST_CST_INPUT_FILES:
                if file_role in sorted_cst_input_files:
                    for file_prefix in sorted_cst_input_files[file_role]:
                        file_name = file_template.format(prefix=file_prefix, suffix="")
                        current_file_input = sorted_cst_input_files[file_role][file_prefix][0]
                        self.algoassert(not sh.path.exists(file_name),
                                        "The file {} already exists. It should not.".format(file_name))
                        sh.cp(current_file_input.rh.container.iotarget(), file_name, intent="in")

            # Deal with other input files (gridpoint and spectral)
            for (file_role, file_template) in self.LIST_INPUT_FILES:
                if file_role in sorted_input_files:
                    for file_prefix in sorted_input_files[file_role]:
                        file_name = file_template.format(prefix=file_prefix, suffix="")
                        current_file_input = sorted_input_files[file_role][file_prefix].pop()
                        self.algoassert(not sh.path.exists(file_name),
                                        "The file {} already exists. It should not.".format(file_name))
                        sh.cp(current_file_input.rh.container.iotarget(), file_name, intent="in")

            if self.clim:
                # Find the right climatology file
                current_month = date.Month(current_validity)
                self.climfile_fixer(rh, convkind='modelclim', month=current_month,
                                    inputrole=('GlobalClim', 'InitialClim'),
                                    inputkind='clim_model')

            # Standard execution
            super(C901, self).execute(rh, opts)
            # Move the output file
            current_term = current_file_input.rh.resource.term
            sh.move(output_name, output_name + "+{}".format(current_term.fmthm))
            # Cat all the listings into a single one
            sh.cat(self.OUTPUT_LISTING_NAME, output='NODE.all')
            # Remove unneeded files
            sh.rmall(deleted_spectral_file_SH, deleted_gridpoint_file_GG, deleted_gridpoint_file_UA,
                     'std*', self.OUTPUT_LISTING_NAME)
