#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import numpy as np
import random
import os
from vortex.algo.components import ParaBlindRun, TaylorRun, Parallel
from vortex.tools.parallelism import VortexWorkerBlindRun, TaylorVortexWorker
from deterministic import Surfex_Parallel
from bronx.stdtypes.date import Date

import footprints
from __builtin__ import str
logger = footprints.loggers.getLogger(__name__)

from snowtools.tools.change_prep import prep_tomodify
from snowtools.utils.resources import get_file_period, save_file_period, save_file_date
from snowtools.tools.update_namelist import update_surfex_namelist_object
from snowtools.utils.ESCROCsubensembles import ESCROC_subensembles
from snowtools.tasks.vortex_kitchen import vortex_conf_file


class Surfex_Member(VortexWorkerBlindRun):
    '''This algo component is designed to run one member of SURFEX experiments without MPI parallelization.'''

    _footprint = dict(
        info = 'AlgoComponent designed to run one member of SURFEX-Crocus experiment without MPI parallelization.',
        attr = dict(
            kind = dict(
                values = ['escroc'],
            ),

            binary = dict(
                values = ['OFFLINE'],
            ),

            datebegin   = dict(
                info = "The first date of the simulation.",
                type = Date,
                optional = False
            ),

            dateend = dict(
                info = "The final date of the simulation.",
                type = Date,
                optional = False
            ),

            dateinit = dict(
                info = "The initialization date if different from the starting date.",
                type = Date,
                optional = True,
                default = '[datebegin]'
            ),

            threshold = dict(
                info = "The initialization date if different from the starting date.",
                type = int,
                optional = True,
                default = -999
            ),

            physical_options = dict(
                info = "Dictionnary of ESCROC physical options",
                type = dict,
                optional = True,
                default = {}
            ),

            snow_parameters = dict(
                info = "Dictionnary of ESCROC snow physical parameters",
                type = dict,
                optional = True,
                default = {}
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = False
            ),
            nforcing = dict(
                info = "Number of ensemblist forcing (soda-deterministic : 1, default-escroc = 0)",
                type = int,
                optional = True,
                default = 0,
            ),
        )
    )

    def vortex_task(self, **kwargs):

        rdict = dict(rc=True)
        rundir = self.system.getcwd()
        if self.subdir is not None:
            thisdir = self.system.path.join(rundir, self.subdir)
            with self.system.cdcontext(self.subdir, create=True):
                sys.stdout = open(self.name + ".out", "a", buffering=0)
                sys.stderr = open(self.name + "_error.out", "a", buffering=0)
                self._surfex_commons(rundir, thisdir)

        else:
            thisdir = rundir
            sys.stdout = open(self.name + ".out", "a", buffering=0)
            sys.stderr = open(self.name + "_error.out", "a", buffering=0)
            self._surfex_commons(rundir, thisdir)

        return rdict

    def modify_prep(self, datebegin_this_run):
        ''' The PREP file needs to be modified if the init date differs from the starting date
         or if a threshold needs to be applied on snow water equivalent.'''

        modif_swe = self.threshold > 0 and datebegin_this_run.month == 8 and datebegin_this_run.day == 1
        modif_date = datebegin_this_run == self.datebegin and self.datebegin != self.dateinit
        modif = modif_swe or modif_date

        if modif:
            prep = prep_tomodify("PREP.nc")

            if modif_swe:
                print "APPLY THRESHOLD ON SWE."
                prep.apply_swe_threshold(self.threshold)

            if modif_date:
                print "CHANGE DATE OF THE PREP FILE."
                prep.change_date(self.datebegin)

            prep.close()
        else:
            print "DO NOT CHANGE THE PREP FILE."

    def find_namelists(self, opts=None):
        '''Duplicated method with the Surfex Worker used by the S2M_component class inheriting from ParaBlindrun'''
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [x.rh for x in self.context.sequence.effective_inputs(kind='namelist')]
        self.system.subtitle('Namelist candidates')
        for nam in namcandidates:
            nam.quickview()
        return namcandidates

    def set_env(self, rundir):
        inputs = [x.rh for x in self.context.sequence.effective_inputs()]
        # print 'DBUG'
        # print self.context.sequence.effective_inputs()
        # print dir(self.context.sequence.effective_inputs())
        # print inputs

    def _surfex_commons(self, rundir, thisdir):
        if self.nforcing > 0:  # soda case
            self.set_env(thisdir)
        else:
            self.set_env(rundir)

        list_files_copy = ["OPTIONS.nam"]
        list_files_link = ["PGD.nc", "PREP.nc", "METADATA.xml", "ecoclimapI_covers_param.bin", "ecoclimapII_eu_covers_param.bin", "drdt_bst_fit_60.nc"]
        for required_copy in list_files_copy:
            if not self.system.path.exists(required_copy):
                self.system.cp(self.system.path.join(rundir, required_copy), required_copy)
        for required_link in list_files_link:
            if not self.system.path.exists(required_link):
                self.system.cp(self.system.path.join(rundir, required_link), required_link)

        self._surfex_task(rundir, thisdir)

    def _surfex_task(self, rundir, thisdir):

        namelist_ready = False
        need_other_run = True
        datebegin_this_run = self.datebegin

        while need_other_run:

            # Modification of the PREP file
            self.modify_prep(datebegin_this_run)

            # Get the first file covering part of the whole simulation period
            if self.nforcing > 0:
                dateforcbegin, dateforcend = get_file_period("FORCING", thisdir, datebegin_this_run, self.dateend)
                dateend_this_run = min(self.dateend, dateforcend)
                print self.dateend
                print dateforcend
                print dateend_this_run
            else:

                dateforcbegin, dateforcend = get_file_period("FORCING", rundir, datebegin_this_run, self.dateend)
                dateend_this_run = min(self.dateend, dateforcend)
            if not namelist_ready:
                available_namelists = self.find_namelists()
                if len(available_namelists) > 1:
                    print "WARNING SEVERAL NAMELISTS AVAILABLE !!!"
                for namelist in available_namelists:
                    # Update the contents of the namelist (date and location)
                    # Location taken in the FORCING file.
                    newcontent = update_surfex_namelist_object(namelist.contents, self.datebegin, dateend = self.dateend, updateloc=False, physicaloptions=self.physical_options, snowparameters=self.snow_parameters)
                    newnam = footprints.proxy.container(filename=namelist.container.basename)
                    newcontent.rewrite(newnam)
                    newnam.close()

                namelist_ready = True

            # Run surfex offline
            list_name = self.system.path.join(thisdir, 'offline.out')
            self.local_spawn(list_name)

            # Copy the SURFOUT file for next iteration
            self.system.cp("SURFOUT.nc", "PREP.nc")

            # Rename outputs with the dates
            save_file_date(".", "SURFOUT", dateend_this_run, newprefix="PREP")
            save_file_period(".", "ISBA_PROGNOSTIC.OUT", datebegin_this_run, dateend_this_run, newprefix="PRO")

            # Remove the symbolic link for next iteration
            self.system.remove("FORCING.nc")

            # Prepare next iteration if needed
            datebegin_this_run = dateend_this_run
            need_other_run = dateforcend < self.dateend


class Surfex_Ensemble(ParaBlindRun):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = ['escroc'],
            ),

            binary = dict(
                values = ['OFFLINE'],
            ),

            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = False
            ),
            datebegin = dict(
                info = "The first date of the simulation.",
                type = Date,
                optional = False
            ),

            dateend = dict(
                info = "The final date of the simulation.",
                type = Date,
                optional = False
            ),

            dateinit = dict(
                info = "The initialization date if different from the starting date.",
                type = Date,
                optional = True,
                default = '[datebegin]'
            ),

            threshold = dict(
                info = "The initialization date if different from the starting date.",
                type = int,
                optional = True,
                default = -999
            ),
            subensemble = dict(
                info = "Name of the subensemble (define which physical options are used",
                values = ["E1", "E2", "Crocus", "E1tartes", "E1notartes"]
            ),
            nforcing = dict(
                info = "Number of ensemblist forcing (soda-deterministic : 1, default (escroc : 0)",
                type = int,
                optional = True,
                default = 0,
            ),
            confvapp = dict(
                info = "vapp",
                type = str,
                optional = True,
                default = None
            ),
            confvconf = dict(
                info = "vconf",
                type = str,
                optional = True,
                default = None
            ),
            stopcount = dict(
                info = 'counter for stop steps in the assim sequence',
                type = int,
                optional = True,
                default = 1,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Surfex_Ensemble, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1
        self.subdirs = ['mb{0:04d}'.format(m) for m in self.members]

        self.escroc = ESCROC_subensembles(self.subensemble, self.members)
        self.physical_options = self.escroc.physical_options
        self.snow_parameters = self.escroc.snow_parameters
        self.membersId = self.escroc.members  # Escroc members ids in case of rand selection for ex.
        print('stopcount :', self.stopcount)
        if self.stopcount == 1:
            print('')
            print('copying the fuck conf file')
            print(os.environ['WORKDIR'] + '/' + self.confvapp + '/' + self.confvconf + '/conf/' + self.confvapp + '_' + self.confvconf + '.ini', self.confvapp + '_' + self.confvconf + '.ini')
            self.system.cp(os.environ['WORKDIR'] + '/' + self.confvapp + '/' + self.confvconf + '/conf/' + self.confvapp + '_' + self.confvconf + '.ini', self.confvapp + '_' + self.confvconf + '.ini')
        # counter for stop (assim + pauses) steps in conf file previously copied to currdir
        conffile = vortex_conf_file(self.confvapp + '_' + self.confvconf + '.ini', 'a')
        conffile.write_field('membersId_' + '{0:03d}'.format(self.stopcount), self.membersId)
        conffile.close()

        print('subdirs, physical_options, parameters')
        print(type(self.subdirs), type(self.physical_options), type(self.snow_parameters))
        print(len(self.subdirs), len(self.physical_options), len(self.snow_parameters))

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Surfex_Ensemble, self)._default_common_instructions(rh, opts)
        for attribute in ["datebegin", "dateend", "dateinit", "threshold", "binary", "nforcing"]:
            ddict[attribute] = getattr(self, attribute)
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Note: The number of members and the name of the subdirectories could be
        # auto-detected using the sequence
        self._add_instructions(common_i, dict(subdir=self.subdirs, physical_options=self.physical_options, snow_parameters=self.snow_parameters))
        self._default_post_execute(rh, opts)


class SodaWorker(Parallel):
    '''
    worker for a SODA run (designed for Particle filtering for snow)
    @author: B. Cluzet 2018-05-24
    '''
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

        self.mbdirs = ['../mb{0:04d}'.format(m) for m in self.members]

        os.chdir('workSODA')

        # symbolic links for each prep from each member dir to the soda dir
        jj = 0
        for dirIt in self.mbdirs:
            os.symlink(dirIt + '/PREP_' + self.dateassim.ymdh + '.nc', 'PREP_' + self.dateassim.ymdHh + '_PF_ENS' + str(jj + 1) + '.nc' )
            jj += 1
        # symbolic link from a virtual PREP.nc to the first member (for SODA date-reading reasons)
        os.symlink(self.mbdirs[0] + '/PREP_' + self.dateassim.ymdh + '.nc', 'PREP.nc' )

        # the following should be done only once on the first soda day
        if not os.path.islink('PGD.nc'):
            os.symlink('../PGD.nc', 'PGD.nc')
            os.symlink('../OPTIONS.nam', 'OPTIONS.nam')  # take the first member namelist since the root one NENS might not be properly updated by the user
            os.symlink('../ecoclimapI_covers_param.bin', 'ecoclimapI_covers_param.bin')
            os.symlink('../ecoclimapII_eu_covers_param.bin', 'ecoclimapII_eu_covers_param.bin')
            os.symlink('../SODA', 'SODA')

    def execute(self, rh, opts):
        # run SODA
        super(SodaWorker, self).execute(rh, opts)

    def postfix(self, rh, opts):
        # rename and mix surfout files for next offline assim
        # rename background preps
        # delete soda symbolic links
        os.unlink('PREP.nc')

        memberslistmix = self.members
        random.shuffle(memberslistmix)
        jj = 0
        for dirIt in self.mbdirs:
            strmixnumber = str(memberslistmix[jj])
            os.unlink('PREP_' + self.dateassim.ymdHh + '_PF_ENS' + str(jj + 1) + '.nc')
            self.system.mv(dirIt + "/PREP_" + self.dateassim.ymdh + ".nc", dirIt + "/PREP_" + self.dateassim.ymdh + "_bg.nc")
            self.system.mv("SURFOUT" + strmixnumber + ".nc", dirIt + "/PREP_" + self.dateassim.ymdh + ".nc")
            jj += 1

        # adapt the following line whenever the ISBA_analysis is available
        # save_file_period(".", "ISBA_PROGNOSTIC.OUT", datebegin_this_run, dateend_this_run, newprefix="PRO")

        # Remove the symbolic link for next iteration (useless for now since filename changes (no overwriting)
        # self.system.remove("FORCING.nc")

        # Prepare next iteration if needed
        # datebegin_this_run = dateend_this_run
        # need_other_run = dateforcend < self.dateend
        os.chdir('..')
