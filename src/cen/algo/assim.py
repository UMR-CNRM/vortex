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

logger = loggers.getLogger(__name__)

echecker = ExternalCodeImportChecker('snowtools')
with echecker:
    from snowtools.tools.update_namelist import update_namelist_object_nmembers


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
