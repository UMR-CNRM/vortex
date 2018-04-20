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
from snowtools.scores.list_scores import ESCROC_list_scores, scores_file, ensemble_scores_file
from snowtools.scores.ensemble import ESCROC_EnsembleScores

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


class ESCROC_subensembles(dict):

    def __init__(self, subensemble, members):

        self.dicoptrad = {"B60": "B92", "B10": "B92", "TAR": "TA3", "TA+": "TA4"}
        self.dicageing = {"B60": 60, "B10": 10, "B120": 120, "B180": 180, "B240": 240, "TAR": 60, "TA+": 60}

        self.dicoptturb = {"RIL": "RIL", "RI1": "RIL", "RI2": "RIL", "M98": "M98"}

        self.dicz0 = {"RIL": 0.001, "RI1": 0.001, "RI2": 0.001, "M98": 0.001}
        self.dicrimax = {"RIL": 0.2, "RI1": 0.1, "RI2": 0.026, "M98": 0.026}
        self.dicxcvheatf = {"CV50000": 1.0, "CV30000": 0.6, "CV10000": 0.2}

        if subensemble == "E1":
            self.physical_options, self.snow_parameters = self.E1(members)

        elif subensemble in ["E2", "E2CLEAR"] :
            self.physical_options, self.snow_parameters = self.E2(members)

        elif subensemble in ["Crocus"] :
            self.physical_options, self.snow_parameters = self.Crocus(members)

    def E1(self, members):

        physical_options = []
        snow_parameters = []
        mb = 0

        for snowfall in ['V12', 'S02', 'A76']:
            for metamo in ['C13', 'F06', 'S-F']:
                for radiation in ['B60', 'B10', 'TAR', 'TA+']:
                    for turb in ['RIL', 'RI1', 'RI2', 'M98']:
                        for cond in ['Y81', 'I02']:
                            for holding in ['B92', 'SPK', 'B02']:
                                for compaction in ['B92', 'S14', 'T11']:
                                    for cv in ['CV10000', 'CV30000', 'CV50000']:

                                            mb += 1
                                            if mb in members:
                                                po, sp = self.convert_options(snowfall, metamo, radiation, turb, cond, holding, compaction, cv)
                                                physical_options.append(po)
                                                snow_parameters.append(sp)

        return physical_options, snow_parameters
    
    def E2(self, members):

        members = {1: ['V12', 'C13', 'B60', 'RI1', 'Y81', 'SPK', 'B92', 'CV30000'],
                   2: ['V12', 'C13', 'B60', 'RI1', 'I02', 'B92', 'S14', 'CV30000'],
                   3: ['V12', 'C13', 'B60', 'RI2', 'Y81', 'B92', 'S14', 'CV30000'],
                   4: ['V12', 'C13', 'B10', 'RIL', 'Y81', 'B92', 'B92', 'CV30000'],
                   5: ['V12', 'C13', 'B60', 'RI1', 'I02', 'SPK', 'T11', 'CV50000'],
                   6: ['V12', 'C13', 'B60', 'RI2', 'I02', 'SPK', 'S14', 'CV50000'],
                   7: ['V12', 'C13', 'B10', 'RI1', 'I02', 'SPK', 'B92', 'CV30000'],
                   8: ['V12', 'F06', 'B60', 'RIL', 'Y81', 'B92', 'S14', 'CV30000'],
                   9: ['V12', 'F06', 'B60', 'RIL', 'Y81', 'SPK', 'S14', 'CV50000'],
                   10: ['V12', 'F06', 'B60', 'RIL', 'I02', 'B92', 'T11', 'CV50000'],
                   11: ['V12', 'S-F', 'B60', 'RI1', 'I02', 'B92', 'S14', 'CV30000'],
                   12: ['V12', 'S-F', 'B10', 'RI2', 'I02', 'SPK', 'B92', 'CV30000'],
                   13: ['V12', 'S-F', 'B60', 'RIL', 'Y81', 'SPK', 'S14', 'CV50000'],
                   14: ['V12', 'S-F', 'B60', 'RIL', 'Y81', 'SPK', 'S14', 'CV30000'],
                   15: ['V12', 'S-F', 'B60', 'M98', 'Y81', 'SPK', 'B92', 'CV30000'],
                   16: ['V12', 'S-F', 'B10', 'RIL', 'I02', 'SPK', 'B92', 'CV30000'],
                   17: ['S02', 'C13', 'B60', 'M98', 'Y81', 'B92', 'S14', 'CV30000'],
                   18: ['S02', 'C13', 'B10', 'RI1', 'I02', 'B92', 'B92', 'CV30000'],
                   19: ['S02', 'F06', 'B60', 'RIL', 'Y81', 'B92', 'S14', 'CV50000'],
                   20: ['S02', 'F06', 'B60', 'M98', 'I02', 'B92', 'B92', 'CV30000'],
                   21: ['S02', 'F06', 'B60', 'M98', 'I02', 'SPK', 'B92', 'CV30000'],
                   22: ['S02', 'F06', 'B60', 'RI1', 'Y81', 'SPK', 'B92', 'CV30000'],
                   23: ['S02', 'F06', 'B10', 'RIL', 'I02', 'SPK', 'B92', 'CV30000'],
                   24: ['S02', 'F06', 'B10', 'RI1', 'I02', 'SPK', 'B92', 'CV30000'],
                   25: ['S02', 'S-F', 'B60', 'RIL', 'I02', 'B92', 'B92', 'CV50000'],
                   26: ['S02', 'S-F', 'B60', 'RIL', 'I02', 'SPK', 'S14', 'CV50000'],
                   27: ['S02', 'S-F', 'B60', 'RI1', 'I02', 'SPK', 'B92', 'CV30000'],
                   28: ['S02', 'S-F', 'B60', 'RIL', 'I02', 'SPK', 'S14', 'CV50000'],
                   29: ['A76', 'F06', 'B60', 'M98', 'I02', 'B02', 'S14', 'CV30000'],
                   30: ['A76', 'F06', 'B60', 'M98', 'I02', 'SPK', 'B92', 'CV30000'],
                   31: ['A76', 'F06', 'B10', 'RIL', 'I02', 'B92', 'B92', 'CV30000'],
                   32: ['A76', 'S-F', 'B10', 'RIL', 'Y81', 'B92', 'B92', 'CV30000'],
                   33: ['A76', 'S-F', 'B10', 'RI2', 'I02', 'B92', 'B92', 'CV30000'],
                   34: ['A76', 'S-F', 'B60', 'RIL', 'Y81', 'SPK', 'S14', 'CV50000'],
                   35: ['A76', 'S-F', 'B60', 'RI1', 'Y81', 'SPK', 'B92', 'CV30000']}

        physical_options = []
        snow_parameters = []

        for mb in members:

            po, sp = self.convert_options(*members[mb])
            physical_options.append(po)
            snow_parameters.append(sp)

        return physical_options, snow_parameters

    def Crocus(self, members):

        members = {1: ['V12', 'C13', 'B60', 'RI1', 'Y81', 'B92', 'B92', 'CV30000']}

        physical_options = []
        snow_parameters = []

        for mb in members:

            po, sp = self.convert_options(*members[mb])
            physical_options.append(po)
            snow_parameters.append(sp)

        return physical_options, snow_parameters

    def convert_options(self, snowfall, metamo, radiation, turb, cond, holding, compaction, cv):

        physical_options = dict(
            csnowfall=snowfall,
            csnowmetamo=metamo,
            csnowrad=self.dicoptrad[radiation],
            csnowcond=cond,
            csnowcomp=compaction,
            csnowhold=holding,
            csnowres=self.dicoptturb[turb]
        )

        snow_parameters = dict(
            xvaging_noglacier=self.dicageing[radiation],
            xz0sn=self.dicz0[turb],
            x_ri_max=self.dicrimax[turb],
            xcvheatf=self.dicxcvheatf[cv],
        )

        return physical_options, snow_parameters


class Escroc_Score_Member(TaylorVortexWorker):
    _footprint = dict(
        info = 'AlgoComponent designed to run one member of SURFEX-Crocus experiment without MPI parallelization.',
        attr = dict(
            kind = dict(
                values = ['scores_escroc'],
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

            list_scores = dict(
                info = "List of scores to compute",
                type = list,
                optional = False
            ),

            list_var = dict(
                info = "List of variables for which we want to compute the scores",
                type = list,
                optional = False
            ),

            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = False
            )
        )
    )

    def vortex_task(self, **kwargs):

        rdict = dict(rc=True)

        sys.stdout = open(str(self.members[0]) + "_" + self.name + ".out", "a", buffering=0)
        sys.stderr = open(str(self.members[0]) + "_" + self.name + "_error.out", "a", buffering=0)

        list_pro = ["PRO_" + self.datebegin.ymdh + "_" + self.dateend.ymdh + '_mb{0:04d}'.format(member) + ".nc" for member in self.members]
        print list_pro
        E = ESCROC_list_scores()
        rdict["scores"] = E.compute_scores_allmembers(list_pro, "obs_insitu.nc", self.list_scores, self.list_var)
        rdict["members"] = self.members  # because in the report the members can be in a different order

        return rdict

    def set_env(self, rundir):
        inputs = [x.rh for x in self.context.sequence.effective_inputs()]
        print 'DBUG'
        print self.context.sequence.effective_inputs()
        print dir(self.context.sequence.effective_inputs())
        print inputs


class Escroc_Score_Ensemble(TaylorRun):
    _footprint = dict(
        info = 'AlgoComponent that compute ESCROC scores for the full ensemble',
        attr = dict(
            engine = dict(
                values = ['blind']
            ),

            kind = dict(
                values = ['scores_escroc'],
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

            list_scores = dict(
                info = "List of scores to compute",
                type = list,
                optional = False
            ),

            list_var = dict(
                info = "List of variables for which we want to compute the scores",
                type = list,
                optional = False
            ),

        )
    )

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Escroc_Score_Ensemble, self)._default_common_instructions(rh, opts)
        for attribute in ["datebegin", "dateend", "list_var", "list_scores"]:
            ddict[attribute] = getattr(self, attribute)
        return ddict

    def _default_pre_execute(self, rh, opts):
        super(Escroc_Score_Ensemble, self)._default_pre_execute(rh, opts)
        self.local_members = self.split_members_by_task()

    def _default_post_execute(self, rh, opts):
        super(Escroc_Score_Ensemble, self)._default_post_execute(rh, opts)
        report = self._boss.get_report()

        scores_all = np.empty((len(self.list_scores), len(self.members), len(self.list_var), 1), float)

        for task in range(0, self.ntasks):
            scores_task = report["workers_report"][task]["report"]["scores"]
#             members_task = np.array(self.local_members[task]) - self.local_members[0][0]
            members_task = np.array(report["workers_report"][task]["report"]["members"]) - 1
            print "DEBUG"
            print members_task
            print scores_task[:, :, :].shape
            print scores_all[:, members_task, :, :].shape
            scores_all[:, members_task, :, :] = scores_task[:, :, :, np.newaxis]

        scores_dataset = scores_file("scores.nc", "w")
        for s, score in enumerate(self.list_scores):
            scores_dataset.write(score, scores_all[s, :, :])

        scores_dataset.close()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)

        print "local members"
        print self.local_members[:]

        self._add_instructions(common_i, dict(members=self.local_members))
        self._default_post_execute(rh, opts)

    def split_members_by_task(self):
        nmembers = len(self.members)

        # Numbers of members by task
        nmembers_by_task_min = nmembers / self.ntasks
        nmembers_by_task_max = nmembers_by_task_min + 1

        # Numbers of tasks running with the maximum value
        ntasks_with_max = nmembers % self.ntasks

        local_members = []
        firstmember = 1

        for task in range(0, self.ntasks):
            if task < ntasks_with_max:
                nmembers_by_task = nmembers_by_task_max
            else:
                nmembers_by_task = nmembers_by_task_min

            lastmember = firstmember + nmembers_by_task - 1
            local_members.append(range(firstmember, min(lastmember, nmembers) + 1))
            firstmember = lastmember + 1

        return local_members


class Escroc_Score_Subensemble(TaylorVortexWorker):
    _footprint = dict(
        info = 'AlgoComponent designed to compute ensemble scores for a given subensemble.',
        attr = dict(
            kind = dict(
                values = ['optim_escroc'],
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

            list_scores = dict(
                info = "List of scores to compute",
                type = list,
                optional = False
            ),

            list_var = dict(
                info = "List of variables for which we want to compute the scores",
                type = list,
                optional = False
            ),

            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = False
            )
        )
    )

    def vortex_task(self, **kwargs):

        rdict = dict(rc=True)

        sys.stdout = open(str(self.members[0]) + "_" + self.name + ".out", "a", buffering=0)
        sys.stderr = open(str(self.members[0]) + "_" + self.name + "_error.out", "a", buffering=0)

        list_pro = ["PRO_" + self.datebegin.ymdh + "_" + self.dateend.ymdh + '_mb{0:04d}'.format(member) + ".nc" for member in self.members]
        print list_pro
        for var in self.list_var:
            E = ESCROC_EnsembleScores(list_pro, "obs_insitu.nc", var)
            crps = E.CRPS()
            dispersion, rmse, ss = E.dispersionEnsemble()
        rdict["scores"] = [crps, dispersion, rmse, ss]
        rdict["members"] = self.members  # because in the report the members can be in a different order

        return rdict

    def set_env(self, rundir):
        inputs = [x.rh for x in self.context.sequence.effective_inputs()]
        print 'DBUG'
        print self.context.sequence.effective_inputs()
        print dir(self.context.sequence.effective_inputs())
        print inputs


class Escroc_Optim_Ensemble(TaylorRun):
    _footprint = dict(
        info = 'AlgoComponent that compute ESCROC scores for the full ensemble',
        attr = dict(
            engine = dict(
                values = ['blind']
            ),

            kind = dict(
                values = ['optim_escroc'],
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

            list_scores = dict(
                info = "List of scores to compute",
                type = list,
                optional = False
            ),

            list_var = dict(
                info = "List of variables for which we want to compute the scores",
                type = list,
                optional = False
            ),
            
            niter = dict(
                info = "Number of iterations",
                type = int,
                optional = True,
                default = 1000
            ),
        )
    )

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Escroc_Optim_Ensemble, self)._default_common_instructions(rh, opts)
        for attribute in ["datebegin", "dateend", "list_var", "list_scores"]:
            ddict[attribute] = getattr(self, attribute)
        return ddict

    def _default_pre_execute(self, rh, opts):
        super(Escroc_Optim_Ensemble, self)._default_pre_execute(rh, opts)
        if len(self.members) < 35:
            nmembers = len(self.members)
        else:
            nmembers = 35
        self.local_members = self.select_random_members(nmembers=nmembers, niter=self.niter)

    def _default_post_execute(self, rh, opts):
        super(Escroc_Optim_Ensemble, self)._default_post_execute(rh, opts)
        report = self._boss.get_report()

        ntasks = len(report["workers_report"])
        crps = np.empty(ntasks, float)
        dispersion = np.empty(ntasks, float)
        rmse = np.empty(ntasks, float)
        ss =  np.empty(ntasks, float)
        members = np.empty((ntasks, 35), int)
        

        
        for task in range(0, ntasks):
            crps[task], dispersion[task], rmse[task], ss[task] = report["workers_report"][task]["report"]["scores"]
            members[task, :] = np.array(report["workers_report"][task]["report"]["members"])

        scores_dataset = ensemble_scores_file("scores.nc", "w")
        scores_dataset.write_members(members)
        scores_dataset.write("crps", crps)
        scores_dataset.write("dispersion", dispersion)
        scores_dataset.write("rmse", rmse)
        scores_dataset.write("ss", ss)        

        scores_dataset.close()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)

        print "local members"
        print self.local_members[:]

        self._add_instructions(common_i, dict(members=self.local_members))
        self._default_post_execute(rh, opts)

    def select_random_members(self, nmembers=35, niter=1000):

        if niter==1 and len(self.members) == nmembers:
            return [self.members[:]]
        else:
            # Initialization
            # We want that all sites are tested with the same subensembles, this is why we fix the argument of random.seed()
            random.seed(0)
            local_members=[]
            
            for iter in range(0,niter):
                listTest = []
                candidates = self.members[:]
                print candidates
                print type(candidates)
                # Randomly select nmembers members
                for m in range(0, nmembers):
                    member=random.choice(candidates) 
                    listTest.append(member)
                    candidates.remove(member)
                local_members.append(listTest)

            return local_members





