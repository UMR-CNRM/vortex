# -*- coding: utf-8 -*-

"""
Algo Components for ensemble S2M simulations.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from bronx.stdtypes.date import Date
from bronx.syntax.externalcode import ExternalCodeImportChecker

import footprints
from vortex.algo.components import Parallel, AlgoComponent
from vortex.syntax.stdattrs import a_date
from cen.algo.ensemble import PrepareForcingWorker, PrepareForcingComponent

logger = loggers.getLogger(__name__)

echecker = ExternalCodeImportChecker('snowtools')
with echecker:
    from snowtools.tools.update_namelist import update_namelist_object_nmembers
    from snowtools.tools.perturb_forcing import forcinput_perturb
    from snowtools.utils.resources import get_file_period, save_file_period


class SodaWorker(Parallel):
    """
    worker for a SODA run (designed for Particle filtering for snow)
    @author: B. Cluzet 2018-05-24
    """
    _footprint = dict(
        info = 'AlgoComponent that runs domain-parallelized soda',
        attr = dict(
            kind = dict(
                values = ['s2m_soda']
            ),
            binary = dict(
                values = ['SODA'],
                optional = False
            ),
            datebegin=dict(
                type = Date,
                optional = True
            ),
            dateend=dict(
                type = Date,
                optional = True
            ),
            dateassim=dict(
                type = Date,
                optional = False
            ),
            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = False
            ),
        )
    )

    def prepare(self, rh, opts):
        super(SodaWorker, self).prepare(rh, opts)

        self.mbdirs = ['mb{0:04d}'.format(m + 1) for m in range(len(self.members))]

        # symbolic links for each prep from each member dir to the soda dir
        jj = 0
        for dirIt in self.mbdirs:
            self.system.symlink(dirIt + '/PREP_' + self.dateassim.ymdh + '.nc', 'PREP_' + self.dateassim.ymdHh +
                                '_PF_ENS' + str(jj + 1) + '.nc')
            jj += 1
        # symbolic link from a virtual PREP.nc to the first member (for SODA date-reading reasons)
        self.system.symlink(self.mbdirs[0] + '/PREP_' + self.dateassim.ymdh + '.nc', 'PREP.nc')

    def execute(self, rh, opts):
        # run SODA
        super(SodaWorker, self).execute(rh, opts)

    def postfix(self, rh, opts):
        # rename ((and mix)) surfout files for next offline assim
        # rename background preps
        # delete soda symbolic links
        self.system.remove('PREP.nc')
        memberslist = range(1, len(self.members) + 1)

        for dirIt, mb in zip(self.mbdirs, memberslist):
            self.system.remove('PREP_' + self.dateassim.ymdHh + '_PF_ENS' + str(mb) + '.nc')
            if self.system.path.isfile(dirIt + '/PREP.nc'):  # old task/offline case
                self.system.remove(dirIt + '/PREP.nc')
            self.system.mv(dirIt + "/PREP_" + self.dateassim.ymdh + ".nc", dirIt + "/PREP_" + self.dateassim.ymdh +
                           "_bg.nc")
            self.system.mv("SURFOUT" + str(mb) + ".nc", dirIt + "/PREP_" + self.dateassim.ymdh + ".nc")
            self.system.symlink(dirIt + "/PREP_" + self.dateassim.ymdh + ".nc", dirIt + '/PREP.nc')
            #  above useful only for old task/offline case

        # rename particle file
        if self.system.path.isfile('PART'):
            self.system.mv('PART', 'PART_' + self.dateassim.ymdh + '.txt')
        if self.system.path.isfile('BG_CORR'):
            self.system.mv('BG_CORR', 'BG_CORR_' + self.dateassim.ymdh + '.txt')
        if self.system.path.isfile('IMASK'):
            self.system.mv('IMASK', 'IMASK_' + self.dateassim.ymdh + '.txt')
        if self.system.path.isfile('ALPHA'):
            self.system.mv('ALPHA', 'ALPHA_' + self.dateassim.ymdh + '.txt')


@echecker.disabled_if_unavailable
class Soda_PreProcess(AlgoComponent):
    """Prepare SODA namelist according to configuration file"""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['soda_preprocess']),
            engine = dict(
                optional     = True,
                default   = 'algo'
            ),
            members=dict(
                info="The members that will be processed",
                type=footprints.FPList,
            ),
        )
    )

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [x.rh for x in self.context.sequence.effective_inputs(kind='namelist')]
        self.system.subtitle('Namelist candidates')
        for nam in namcandidates:
            nam.quickview()

        return namcandidates

    def execute(self, rh, opts):

        # Modification of the namelist
        for namelist in self.find_namelists():
            # Update the contents of the namelist (number of members)
            # Location taken in the FORCING file.
            newcontent = update_namelist_object_nmembers(
                namelist.contents,
                nmembers=len(self.members)
            )
            newnam = footprints.proxy.container(filename=namelist.container.basename)
            newcontent.rewrite(newnam)
            newnam.close()


@echecker.disabled_if_unavailable
class PerturbForcingWorker(PrepareForcingWorker):
    """
    Worker that applies stochastic perturbations to a time series of forcing files
    (worker for 1 member).
    """

    _footprint = dict(
        info = 'Apply stochastic perturbations to a forcing file',
        attr = dict(
            kind = dict(
                values = ['perturbforcing']
            ),
            geometry_out = dict(
                info="The resource's massif geometry.",
                type=str,
                optional = True,
                default = None
            )
        )
    )

    def _prepare_forcing_task(self, rundir, thisdir, rdict):

        need_other_forcing = True
        datebegin_this_run = self.datebegin

        while need_other_forcing:

            forcingdir = self.forcingdir(rundir, thisdir)

            # Get the first file covering part of the whole simulation period
            dateforcbegin, dateforcend = get_file_period("FORCING", forcingdir,
                                                         datebegin_this_run, self.dateend)

            self.system.mv("FORCING.nc", "FORCING_OLD.nc")
            forcinput_perturb("FORCING_OLD.nc", "FORCING.nc")

            dateend_this_run = min(self.dateend, dateforcend)

            # Prepare next iteration if needed
            datebegin_this_run = dateend_this_run
            need_other_forcing = dateend_this_run < self.dateend

            save_file_period(thisdir, "FORCING", dateforcbegin, dateforcend)

        return rdict


@echecker.disabled_if_unavailable
class PerturbForcingComponent(PrepareForcingComponent):
    """
    Algo compent that creates an ensemble of forcing files by stochastic perturbations
    of a time series of deterministic input forcing files
    (worker for 1 member).
    """
    _footprint = dict(
        info = 'AlgoComponent that build an ensemble of perturbed forcings from deterministic forcing files',
        attr = dict(
            kind = dict(
                values = ['perturbforcing']
            ),
            members = dict(
                info = "The list of members for output",
                type = footprints.stdtypes.FPList,
            ),
            datebegin = a_date,
            dateend = a_date,
        )
    )

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Contrary to mother class, datebegin and dateend are not used for parallelization.
        subdirs = self.get_subdirs(rh, opts)
        self._add_instructions(common_i, dict(subdir=subdirs))
        self._default_post_execute(rh, opts)

    def get_subdirs(self, rh, opts):
        # In this algo component, the number of members is defined by the user,
        # as there is only 1 single deterministic input
        return ['mb{0:04d}'.format(member) for member in self.members]
