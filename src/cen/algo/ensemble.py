#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from collections import defaultdict
import io
import six

from bronx.stdtypes.date import Date, Period, tomorrow
from bronx.syntax.externalcode import ExternalCodeImportChecker
import footprints

from vortex.algo.components import ParaBlindRun, ParaExpresso
from vortex.tools.parallelism import VortexWorkerBlindRun
from vortex.syntax.stdattrs import a_date
from vortex.util.helpers import InputCheckerError

logger = footprints.loggers.getLogger(__name__)

echecker = ExternalCodeImportChecker('snowtools')
with echecker:
    from snowtools.tools.change_prep import prep_tomodify
    from snowtools.utils.resources import get_file_period, save_file_period, save_file_date
    from snowtools.tools.update_namelist import update_surfex_namelist_object
    from snowtools.tools.change_forcing import forcinput_select, forcinput_tomerge
    from snowtools.utils.infomassifs import infomassifs
    from snowtools.tools.massif_diags import massif_simu
    from snowtools.utils.ESCROCsubensembles import ESCROC_subensembles


class _S2MWorker(VortexWorkerBlindRun):
    '''This algo component is designed to run an S2M task without MPI parallelization.'''

    _abstract  = True
    _footprint = dict(
        info = 'AlgoComponent designed to run an S2M experiment without MPI parallelization.',
        attr = dict(
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
        )
    )

    def vortex_task(self, **kwargs):
        rdict = dict(rc=True)
        rundir = self.system.getcwd()
        if self.subdir is not self.system.path.dirname(rundir):
            thisdir = self.system.path.join(rundir, self.subdir)
            with self.system.cdcontext(self.subdir, create=True):
                self._commons(rundir, thisdir, rdict, **kwargs)

        else:
            thisdir = rundir
            self._commons(rundir, thisdir, rdict, **kwargs)

        return rdict

    def _commons(self, rundir, thisdir, rdict):
        pass

    def mv_if_exists(self, local, dest):
        """Move a file if it exists (intended to deal with output files)."""
        if self.system.path.isfile(local):
            self.system.mv(local, dest)

    def copy_if_exists(self, local, dest):
        """Copy a file if it exists (intended to deal with input files)."""
        if self.system.path.isfile(local):
            self.system.cp(local, dest)

    def link_in(self, local, dest):
        """Link a file (the target is cleaned first)."""
        self.system.remove(dest)
        if self.system.path.isfile(local):
            self.system.symlink(local, dest)

    def link_ifnotprovided(self, local, dest):
        """Link a file if the target does not already exist."""
        if not self.system.path.islink(dest):
            if self.system.path.isfile(local):
                self.system.symlink(local, dest)

    def postfix(self):
        self.system.subtitle('{0:s} : directory listing (post-run)'.format(self.kind))
        for line in self.system.dir():
            print(line)


class GuessWorker(_S2MWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['guess', 'intercep']
            ),
            interpreter = dict(
                values = [ 'python' ]
            ),
        )
    )

    def vortex_task(self, **kwargs):
        ebauche = self.find_ebauche()
        super(GuessWorker, self).vortex_task(ebauche=ebauche)

    def _commons(self, rundir, thisdir, rdict, **kwargs):
        ebauche = kwargs['ebauche']
        if ebauche and not self.system.path.exists(ebauche):
            self.system.symlink(self.system.path.join(rundir, ebauche), ebauche)
        list_name = self.system.path.join(thisdir, self.kind + '.out')
        self.local_spawn(list_name)
        self.postfix()

    def find_ebauche(self, opts=None):
        """Find ebauche namelist in actual context inputs."""
        namcandidates = [x.rh for x in self.context.sequence.effective_inputs(kind='namelist')]
        self.system.subtitle('Namelist candidates')
        ebauche = None
        for nam in namcandidates:
            nam.quickview()
            if nam.container.basename.startswith('EBAUCHE_'):
                ebauche = nam.container.basename

        return ebauche


class _SafranWorker(_S2MWorker):

    _abstract  = True
    _footprint = dict(
        attr = dict(
            datebegin = a_date,
            dateend   = a_date,
            day_begins_at = dict(
                type     = int,
                optional = True,
                default  = 6,
            ),
            posts = dict(
                info = "Switch to activate posts chain (=1) or not (=0)",
                type = int,
                optional = True,
                default = 1,
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(_SafranWorker, self).__init__(*kargs, **kwargs)
        self.set_actual_period()

    def set_actual_period(self):
        """Guess the dates that are to be covered by the forecast"""
        if self.datebegin.hour > self.day_begins_at:
            self.datebegin.day = self.datebegin.day + 1
        self.datebegin.replace(hour=self.day_begins_at, minute=0, second=0, microsecond=0)
        if self.dateend.hour < self.day_begins_at:
            self.dateend.day = self.dateend.day - 1
        self.dateend.replace(hour=self.day_begins_at, minute=0, second=0, microsecond=0)

    @property
    def days(self):
        self._days = defaultdict(list)
        ndays = (self.dateend - self.datebegin).days
        d = self.datebegin
        if ndays > 0:
            for n in range(1, ndays + 1):
                try_dates = [d + Period(hours=h) for h in range(0, 25, 3)]  # We check for 3-hours guess
                self._days[n] = self.get_fichiers_P(try_dates, fatal=False)
                d = d + Period(days=1)
        if ndays == 0:
            logger.warning('The given time period is too short, doing nothing.')
        else:
            logger.warning('datebegin argument must be before dateend argument')
        return self._days

    def _commons(self, rundir, thisdir, rdict, **kwargs):
        _Safran_namelists = ['ANALYSE', 'CENPRAA', 'OBSERVA', 'OBSERVR', 'IMPRESS', 'ADAPT', 'SORTIES', 'MELANGE', 'EBAUCHE']
        for nam in _Safran_namelists:
            self.link_in(self.system.path.join(rundir, nam), nam)

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        _OP_files_common = ['OPlisteo', 'OPlysteo', 'OPlistem', 'Oplystem', 'OPlisteml', 'OPlysteml', 'OPclim',
                            'OPNOmt', 'OPA', 'OPR', 'OPS', 'OPsat', 'OPnoir', 'OPposte']
        _OP_files_individual = ['OPguess', 'OPprevi', 'OPMET', 'OPSA', 'OPSG', 'OPSAP', 'OPSAN']
        for op_file in _OP_files_common:
            if not self.system.path.isfile(op_file):
                with io.open(op_file, 'w') as f:
                    f.write(rundir + '@\n')

        for op_file in _OP_files_individual:
            if not self.system.path.isfile(op_file):
                with io.open(op_file, 'w') as f:
                    f.write(thisdir + '@\n')

        self.system.remove('sapfich')

        print('Running task {0:s}'.format(self.kind))
        for day, dates in self.days.items():
            nech = len(dates) if len(dates) == 9 else 5
            self.sapdat(dates[-1], nech)
            self._safran_task(rundir, thisdir, day, dates, rdict)

        self.postfix()

    def _safran_task(self, rundir, thisdir, rdict):
        """The piece of code specific to a Safran submodule does here."""
        raise NotImplementedError()

    def check_mandatory_resources(self, rdict, filenames):
        outcome = True
        for filename in filenames:
            if not self.system.path.exists(filename):
                logger.error('The %s mandatory flow resources are missing.', filename)
                outcome = False
        rdict['rc'] = rdict['rc'] and outcome
        return outcome

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')
            d.write('0,0,3\n')
            d.write('3,1,3,3\n')
            d.write('0\n')
            d.write('1,1,{0!s}\n'.format(self.posts))

    def get_fichiers_P(self, dates, fatal=True):
        """ Try to guess the corresponding input file"""
        # TODO : Ajouter un control de cohérence sur les cumuls : on ne doit pas
        # mélanger des cumuls sur 6h avec des cumuls sur 24h
        actual_dates = list()
        for date in dates:
            p = 'P{0:s}'.format(date.yymdh)
            if self.system.path.exists(p) and not self.system.path.islink(p):
                actual_dates.append(date)
            else:
                if self.system.path.islink(p):
                    self.system.remove(p)
                # We try to find the P file with format Pyymmddhh_tt (yymmddhh + tt = date)
                # The maximum time is 108h (4 days)
                if date == dates[-1]:
                    # Avoid to take the first P file of the next day
                    # Check for a 6-hour analysis
                    d = date - Period(hours = 6)
                    oldp = 'P{0:s}_{1!s}'.format(d.yymdh, 6)
                    if self.system.path.exists(oldp):
                        self.link_in(oldp, p)
                        actual_dates.append(date)
                    # If there is no 6-hour analysis we need at least a 24h forecast to have a cumulate rr24
                    else:
                        t = 24
                else:
                    t = 0
                while not self.system.path.islink(p) and (t <= 108):
                    d = date - Period(hours = t)
                    oldp = 'P{0:s}_{1!s}'.format(d.yymdh, t)
                    if self.system.path.exists(oldp):
                        self.link_in(oldp, p)
                        actual_dates.append(date)
                    t = t + 3  # 3-hours check
                if not self.system.path.islink(p) and fatal:
                    logger.error('The mandatory flow resources %s is missing.', p)
                    raise InputCheckerError("Some of the mandatory resources are missing.")

        if len(actual_dates) < 5:
            raise InputCheckerError("Not enough guess for date {0:s}, expecting at least 5, got {1:d}".format(dates[0].ymdh, len(actual_dates)))
        elif len(actual_dates) > 5 and len(actual_dates) < 9:
            # We must have either 5 or 9 dates, if not we only keep synoptic ones
            for date in actual_dates:
                if date.hour not in [0, 6, 12, 18]:
                    actual_dates.remove(date)

        return actual_dates


class SafraneWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['safrane']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        nech = len(dates) if len(dates) == 9 else 5
        self.get_fichiers_P(dates)
        for d in dates:
            logger.info('Running date : {0:s}'.format(d.ymdh))
            self.sapdat(d, nech)
            # Creation of the 'sapfich' file containing the name of the output file
            with io.open('sapfich', 'w') as f:
                f.write('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh))
            list_name = self.system.path.join(thisdir, self.kind + d.ymdh + '.out')
            self.local_spawn(list_name)
            # A FAIRE : gérer le fichier fort.79 (mv dans $list/day.$day ?, rejet)


class SypluieWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sypluie']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        self.get_fichiers_P(dates)
        self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5_ARP')
        # Creation of the 'sapfich' file containing the name of the output file
        with io.open('sapfich', 'w') as f:
            f.write('SAPLUI5' + dates[-1].ymdh)
        list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
        self.local_spawn(list_name)
        # A FAIRE : gérer le fichier fort.78 (mv dans $list/day.$day ?, rejet)


class SyrpluieWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrpluie']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        self.get_fichiers_P(dates)
        # Creation of the 'sapfich' file containing the name of the output file
        with io.open('sapfich', 'w') as f:
            f.write('SAPLUI5' + dates[-1].ymdh)
        list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
        self.local_spawn(list_name)
        # le nom de l'output de syrpluie est géré par le fichier sapfich
        # self.mv_if_exists('fort.21', 'SAPLUI5' + dates[-1].ymdh)


class SyvaprWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syvapr']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        if self.check_mandatory_resources(rdict, ['SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh) for d in dates]):
            for j, d in enumerate(dates):
                self.link_in('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh), 'SAFRAN' + six.text_type(j + 1))
            self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5')
            list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
            self.local_spawn(list_name)


class SyvafiWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syvafi']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        # if self.check_mandatory_resources(rdict, ['SAPLUI5' + six.text_type(day), ]):
        for j, d in enumerate(dates):
            self.link_in('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh), 'SAFRAN' + six.text_type(j + 1))
        self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5')
        list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
        self.local_spawn(list_name)
        self.mv_if_exists('fort.90', 'TAL' + dates[-1].ymdh)


class SyrmrrWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrmrr']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):

        if self.check_mandatory_resources(rdict, ['SAPLUI5' + dates[-1].ymdh]):
            self.link_in('SAPLUI5' + dates[-1].ymdh, 'fort.12')
            list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
            self.local_spawn(list_name)
            self.mv_if_exists('fort.13', 'SAPLUI5' + dates[-1].ymdh)
            self.mv_if_exists('fort.14', 'SAPLUI5_ARP' + dates[-1].ymdh)
            self.mv_if_exists('fort.15', 'SAPLUI5_ANA' + dates[-1].ymdh)


class SytistWorker(_SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sytist']
            ),
            execution = dict(
                values = ['analysis', 'forecast']
            )
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5')
        self.link_in('SAPLUI5_ARP' + dates[-1].ymdh, 'SAPLUI5_ARP')
        self.link_in('SAPLUI5_ANA' + dates[-1].ymdh, 'SAPLUI5_ANA')
        if self.check_mandatory_resources(rdict, ['SAPLUI5'] + ['SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh) for d in dates]):
            print(['SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh) for d in dates])
            for j, d in enumerate(dates):
                self.link_in('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh), 'SAFRAN' + six.text_type(j + 1))
            list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
            self.local_spawn(list_name)

            self.mv_if_exists('FORCING_massif.nc', 'FORCING_massif_{0:s}_{1:s}.nc'.format(self.datebegin.ymd6h, self.dateend.ymd6h))
            self.mv_if_exists('FORCING_postes.nc', 'FORCING_postes_{0:s}_{1:s}.nc'.format(self.datebegin.ymd6h, self.dateend.ymd6h))

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')
            if self.execution == 'forecast':
                d.write('0,0,3\n')
            elif self.execution == 'analysis':
                d.write('0,1,0\n')
            d.write('3,1,3,3\n')
            d.write('0\n')
            d.write('1,1,{0!s}\n'.format(self.posts))


@echecker.disabled_if_unavailable
class SurfexWorker(_S2MWorker):
    '''This algo component is designed to run a SURFEX experiment without MPI parallelization.'''

    _footprint = dict(
        info = 'AlgoComponent designed to run a SURFEX experiment without MPI parallelization.',
        attr = dict(
            datebegin = a_date,
            dateend   = a_date,
            dateinit  = a_date,
            kind = dict(
                values = ['deterministic', 'escroc', 'ensmeteo', 'ensmeteo+sytron', 'ensmeteo+escroc'],
            ),
            threshold = dict(
                info = "Threshold to initialise snowdepth",
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
            geometry = dict(
                info = "Area information in case of an execution on a massif geometry",
                type = footprints.stdtypes.FPList,
                optional = True,
                default = None
            ),
            daily = dict(
                info = "If True, split simulations in daily runs",
                type = bool,
                optional = True,
                default = False,
            )
        )
    )

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

    def _commons(self, rundir, thisdir, rdict, **kwargs):

        list_files_copy = ["OPTIONS.nam"]
        list_files_link = ["PGD.nc", "METADATA.xml", "ecoclimapI_covers_param.bin", "ecoclimapII_eu_covers_param.bin", "drdt_bst_fit_60.nc"]
        list_files_link_ifnotprovided = ["PREP.nc"]

        for required_copy in list_files_copy:
            self.copy_if_exists(self.system.path.join(rundir, required_copy), required_copy)
        for required_link in list_files_link:
            self.link_in(self.system.path.join(rundir, required_link), required_link)
        for required_link in list_files_link_ifnotprovided:
            self.link_ifnotprovided(self.system.path.join(rundir, required_link), required_link)

        self._surfex_task(rundir, thisdir, rdict)
        self.postfix()

    def _surfex_task(self, rundir, thisdir, rdict):
        # ESCROC cases: each member will need to have its own namelist
        # meteo ensemble cases: the forcing modification must be applied to all members and the namelist generation requires that
        # the forcing generation has already be done. Therefore, preprocessing is done in the offline algo in all these cases
        # Determinstic cases : the namelist is prepared in the preprocess algo component in order to allow to build PGD and PREP
        namelist_ready = self.kind == 'deterministic'
        need_other_run = True
        need_other_forcing = True
        need_save_forcing = False
        updateloc = True
        datebegin_this_run = self.datebegin

        sytron = self.kind == "ensmeteo+sytron" and self.subdir == "mb036"

        while need_other_run:

            # Modification of the PREP file
            self.modify_prep(datebegin_this_run)

            if need_other_forcing:

                if self.kind == "escroc":
                    # ESCROC only : the forcing files are in the father directory (same forcing for all members)
                    forcingdir = rundir
                elif sytron:
                    # ensmeteo+sytron : the forcing files are supposed to be in the subdirectories of each member except for the sytron member
                    forcingdir = rundir + "/mb035"
                else:
                    # ensmeteo or ensmeteo+escroc : the forcing files are supposed to be in the subdirectories of each member
                    # determinstic case : the forcing file(s) is/are in the only directory
                    forcingdir = thisdir

                if len(self.geometry) > 1:
                    print ("FORCING AGGREGATION")
                    forcinglist = []
                    for massif in self.geometry:
                        dateforcbegin, dateforcend = get_file_period("FORCING", forcingdir + "/" + massif, datebegin_this_run, self.dateend)
                        forcingname = "FORCING_" + massif + ".nc"
                        self.system.mv("FORCING.nc", forcingname)
                        forcinglist.append(forcingname)

                    forcinput_tomerge(forcinglist, "FORCING.nc",)
                    need_save_forcing = True
                else:
                    # Get the first file covering part of the whole simulation period
                    print ("LOOK FOR FORCING")
                    dateforcbegin, dateforcend = get_file_period("FORCING", forcingdir, datebegin_this_run, self.dateend)
                    print ("FORCING FOUND")

                    if self.geometry[0] in ["alp", "pyr", "cor"]:
                        print ("FORCING EXTENSION")
                        liste_massifs = infomassifs().dicArea[self.geometry[0]]
                        liste_aspect  = infomassifs().get_list_aspect(8, ["0", "20", "40"])
                        self.mv_if_exists("FORCING.nc", "FORCING_OLD.nc")
                        forcinput_select('FORCING_OLD.nc', 'FORCING.nc', liste_massifs, 0, 5000, ["0", "20", "40"], liste_aspect)
                        need_save_forcing = True

            if self.daily:
                dateend_this_run = min(tomorrow(base=datebegin_this_run), min(self.dateend, dateforcend))
                need_other_forcing = False
            else:
                dateend_this_run = min(self.dateend, dateforcend)

            if not namelist_ready:
                if sytron:
                    self.copy_if_exists(self.system.path.join(rundir, "OPTIONS_sytron.nam"), "OPTIONS.nam")

                available_namelists = self.find_namelists()
                if len(available_namelists) > 1:
                    print("WARNING SEVERAL NAMELISTS AVAILABLE !!!")
                for namelist in available_namelists:
                    # Update the contents of the namelist (date and location)
                    # Location taken in the FORCING file.
                    print("MODIFY THE NAMELIST:" + namelist.container.basename)
                    newcontent = update_surfex_namelist_object(namelist.contents, datebegin_this_run, dateend=dateend_this_run, updateloc=updateloc, physicaloptions=self.physical_options, snowparameters=self.snow_parameters)
                    newnam = footprints.proxy.container(filename=namelist.container.basename)
                    newcontent.rewrite(newnam)
                    newnam.close()
                if self.daily:
                    updateloc = True
                else:
                    namelist_ready = True

            # Run surfex offline
            list_name = self.system.path.join(thisdir, 'offline.out')
            self.local_spawn(list_name)

            # Copy the SURFOUT file for next iteration
            self.system.cp("SURFOUT.nc", "PREP.nc")

            # Post-process
            pro = massif_simu("ISBA_PROGNOSTIC.OUT.nc", openmode='a')
            pro.massif_natural_risk()
            pro.close()

            # Rename outputs with the dates
            save_file_date(".", "SURFOUT", dateend_this_run, newprefix="PREP")
            save_file_period(".", "ISBA_PROGNOSTIC.OUT", datebegin_this_run, dateend_this_run, newprefix="PRO")

            # Prepare next iteration if needed
            datebegin_this_run = dateend_this_run
            need_other_run = dateend_this_run < self.dateend

            if need_save_forcing and not (need_other_run and not need_other_forcing):
                save_file_period(".", "FORCING", dateforcbegin, dateforcend)
            # Remove the symbolic link for next iteration (not needed since now we rename the forcing just before
#             self.system.remove("FORCING.nc")


class Guess(ParaExpresso):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions of a guess-making script',
        attr = dict(
            kind = dict(
                values = [ 'guess'],
            ),
            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = True
            ),
            interpreter = dict(
                values = [ 'python']
            )
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Guess, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Guess, self)._default_common_instructions(rh, opts)
        ddict['interpreter'] = self.interpreter
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Note: The number of members and the name of the subdirectories could be
        # auto-detected using the sequence
        subdirs = [None, ] if self.members is None else ['mb{0:03d}'.format(m) for m in self.members]
        self._add_instructions(common_i, dict(subdir=subdirs))
        self._default_post_execute(rh, opts)

    def postfix(self, rh, opts):
        pass


class S2MComponent(ParaBlindRun):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = ['safrane', 'syrpluie', 'syrmrr', 'sytist', 'sypluie', 'syvapr',
                          'syvafi', 'intercep'],
            ),
            engine = dict(
                values = ['s2m']),
            datebegin = a_date,
            dateend = a_date,
            execution = dict(
                values = ['analysis', 'forecast'],
                optional = True,
            )
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(S2MComponent, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(S2MComponent, self)._default_common_instructions(rh, opts)
        for attribute in self.footprint_attributes:
            ddict[attribute] = getattr(self, attribute)
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Note: The number of members and the name of the subdirectories could be
        # auto-detected using the sequence
        subdirs = self.get_subdirs(rh, opts)
        self._add_instructions(common_i, dict(subdir=subdirs))
        self._default_post_execute(rh, opts)

    def postfix(self, rh, opts):
        pass

    def get_subdirs(self, rh, opts):
        """Get the subdirectories from the effective inputs"""
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = [am.rh.container.dirname for am in avail_members]
        self.algoassert(len(set(subdirs)) == len(set([am.rh.provider.member for am in avail_members])))

        return list(set(subdirs))

    def role_ref_namebuilder(self):
        return 'Ebauche'


@echecker.disabled_if_unavailable
class SurfexComponent(S2MComponent):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = ['escroc', 'ensmeteo', 'ensmeteo+sytron', 'ensmeteo+escroc']
            ),
            dateinit = dict(
                info = "The initialization date if different from the starting date.",
                type = Date,
                optional = True,
                default = '[datebegin]',
            ),
            threshold = dict(
                info = "The initialization date if different from the starting date.",
                type = int,
                optional = True,
                default = -999
            ),
            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = True,
            ),
            subensemble = dict(
                info = "Name of the escroc subensemble (define which physical options are used)",
                values = ["E1", "E2", "Crocus"],
                optional = True,
            ),
            geometry = dict(
                info = "Area information in case of an execution on a massif geometry",
                type = footprints.stdtypes.FPList,
                optional = True,
                default = None
            ),
            daily = dict(
                info = "If True, split simulations in daily runs",
                type = bool,
                optional = True,
                default = False,
            )
        )
    )

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)

        subdirs = self.get_subdirs(rh, opts)

        if self.subensemble:
            escroc = ESCROC_subensembles(self.subensemble, self.members)
            physical_options = escroc.physical_options
            snow_parameters = escroc.snow_parameters
            self._add_instructions(common_i, dict(subdir=subdirs, physical_options=physical_options, snow_parameters=snow_parameters))
        else:
            self._add_instructions(common_i, dict(subdir=subdirs))
        self._default_post_execute(rh, opts)

    def get_subdirs(self, rh, opts):
        if self.kind == "escroc":
            return ['mb{0:04d}'.format(m) for m in self.members]
        else:
            subdirs = super(SurfexComponent, self).get_subdirs(rh, opts)
            if self.kind == "ensmeteo+sytron":
                subdirs.append('mb036')
            return subdirs

    def role_ref_namebuilder(self):
        return 'Forcing'
