#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import numpy as np
import random

from vortex.algo.components import ParaBlindRun, TaylorRun
from vortex.tools.parallelism import VortexWorkerBlindRun, TaylorVortexWorker

from bronx.stdtypes.date import Date

import footprints
logger = footprints.loggers.getLogger(__name__)

from snowtools.tools.change_prep import prep_tomodify
from snowtools.utils.resources import get_file_period, save_file_period, save_file_date
from snowtools.tools.update_namelist import update_surfex_namelist_object
from snowtools.utils.ESCROCsubensembles import ESCROC_subensembles 


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

                print self.subdir
                print self.physical_options
                print self.snow_parameters

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
        print 'DBUG'
        print self.context.sequence.effective_inputs()
        print dir(self.context.sequence.effective_inputs())
        print inputs

    def _surfex_commons(self, rundir, thisdir):

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
            dateforcbegin, dateforcend = get_file_period("FORCING", rundir, datebegin_this_run, self.dateend)
            dateend_this_run = min(self.dateend, dateforcend)

            if not namelist_ready:
                available_namelists = self.find_namelists()
                if len(available_namelists) > 1:
                    print "WARNING SEVERAL NAMELISTS AVAILABLE !!!"
                for namelist in available_namelists:
                    # Update the contents of the namelist (date and location)
                    # Location taken in the FORCING file.
                    newcontent = update_surfex_namelist_object(namelist.contents, self.datebegin, updateloc=False, physicaloptions=self.physical_options, snowparameters=self.snow_parameters)
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
                values = ["E1", "E2", "Crocus"]
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Surfex_Ensemble, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Surfex_Ensemble, self)._default_common_instructions(rh, opts)
        for attribute in ["datebegin", "dateend", "dateinit", "threshold", "binary"]:
            ddict[attribute] = getattr(self, attribute)
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Note: The number of members and the name of the subdirectories could be
        # auto-detected using the sequence
        subdirs = ['mb{0:04d}'.format(m) for m in self.members]

        escroc = ESCROC_subensembles(self.subensemble, self.members)
        physical_options = escroc.physical_options
        snow_parameters = escroc.snow_parameters

        print type(subdirs), type(physical_options), type(snow_parameters)
        print len(subdirs), len(physical_options), len(snow_parameters)
        self._add_instructions(common_i, dict(subdir=subdirs, physical_options=physical_options, snow_parameters=snow_parameters))
        self._default_post_execute(rh, opts)
