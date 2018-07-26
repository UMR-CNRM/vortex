#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.algo.components import Parallel, AlgoComponent
from bronx.stdtypes.date import Date

import footprints
logger = footprints.loggers.getLogger(__name__)

from snowtools.tools.change_prep import prep_tomodify
from snowtools.utils.resources import get_file_period, save_file_period, save_file_date
from snowtools.tools.update_namelist import update_surfex_namelist_object


class Surfex_PreProcess(AlgoComponent):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['surfex_preprocess']),
            engine = dict(
                optional     = True,
                default   = 'algo'
            ),
            datebegin = dict(
                info = "Date in the namelist to run PREP.",
                type = Date,
            ),
            dateend = dict(
                info = "Date in the namelist to stop OFFLINE.",
                type = Date,
                optional = True,
                default = None
            ),
            forcingname = dict(
                info = "Name of the first forcing file",
                type = str,
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

        # Add forcing preparation

        # Modification of the namelist
        for namelist in self.find_namelists():
            # Update the contents of the namelist (date and location)
            # Location taken in the FORCING file.
            newcontent = update_surfex_namelist_object(namelist.contents, self.datebegin, forcing = self.forcingname, dateend = self.dateend)
            newnam = footprints.proxy.container(filename=namelist.container.basename)
            newcontent.rewrite(newnam)
            newnam.close()


class Pgd_Parallel_from_Forcing(Parallel):
    '''This algo component is designed to run PGD with MPI parallelization and using a FORCING.nc as input for topography.'''
    _footprint = dict(
        info = 'This algo component is designed to run PGD with MPI parallelization and using a FORCING.nc as input for topography.',
        attr = dict(
            kind = dict(values = ['pgd_from_forcing']),
            forcingname = dict(
                info = "Name of the first forcing file",
                type = str,
            ),
            engine = dict(
                optional = True,
                default = 'parallel')
        )
    )

    def execute(self, rh, opts):
        self.system.symlink(self.forcingname, "FORCING.nc")
        super(Pgd_Parallel_from_Forcing, self).execute(rh, opts)
        self.system.remove("FORCING.nc")


class Surfex_Parallel(Parallel):
    '''This algo component is designed to run SURFEX experiments over large domains with MPI parallelization.'''

    _footprint = dict(
        info = 'AlgoComponent designed to run SURFEX experiments over large domains with MPI parallelization.',
        attr = dict(
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
        )
    )

    def execute(self, rh, opts):

        need_other_run = True
        datebegin_this_run = self.datebegin

        while need_other_run:

            # Modification of the PREP file
            self.modify_prep(datebegin_this_run)

            # Get the first file covering part of the whole simulation period
            dateforcbegin, dateforcend = get_file_period("FORCING", ".", datebegin_this_run, self.dateend)
            dateend_this_run = min(self.dateend, dateforcend)

            # Run surfex offline
            super(Surfex_Parallel, self).execute(rh, opts)

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

    def modify_prep(self, datebegin_this_run):
        ''' The PREP file needs to be modified if the init date differs from the starting date
         or if a threshold needs to be applied on snow water equivalent.'''

        modif_swe = self.threshold > 0 and datebegin_this_run.month == 8 and datebegin_this_run.day == 1
        modif_date = datebegin_this_run == self.datebegin and self.datebegin != self.dateinit
        modif = modif_swe or modif_date

        if modif:
            prep = prep_tomodify("PREP.nc")

            if modif_swe:
                print("APPLY THRESHOLD ON SWE.")
                prep.apply_swe_threshold(self.threshold)

            if modif_date:
                print("CHANGE DATE OF THE PREP FILE.")
                prep.change_date(self.datebegin)

            prep.close()
        else:
            print("DO NOT CHANGE THE PREP FILE.")