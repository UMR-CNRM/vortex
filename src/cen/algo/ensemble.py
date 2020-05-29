#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Period, tomorrow
from bronx.syntax.externalcode import ExternalCodeImportChecker
from collections import defaultdict
import footprints
import io
from vortex.algo.components import ParaBlindRun, ParaExpresso, TaylorRun
from vortex.syntax.stdattrs import a_date
from vortex.tools.parallelism import VortexWorkerBlindRun, TaylorVortexWorker
from vortex.tools.systems import ExecutionError
from vortex.util.helpers import InputCheckerError

import six


logger = loggers.getLogger(__name__)

echecker = ExternalCodeImportChecker('snowtools')
with echecker:
    from snowtools.tools.change_prep import prep_tomodify
    from snowtools.utils.resources import get_file_period, save_file_period, save_file_date
    from snowtools.tools.update_namelist import update_surfex_namelist_object
    from snowtools.tools.change_forcing import forcinput_select, forcinput_applymask
    from snowtools.utils.infomassifs import infomassifs
    from snowtools.tools.massif_diags import massif_simu
    from snowtools.utils.ESCROCsubensembles import ESCROC_subensembles
    from snowtools.utils import S2M_standard_file
    from snowtools.utils.FileException import TimeListException


class _S2MWorker(VortexWorkerBlindRun):
    """This algo component is designed to run an S2M task without MPI parallelization."""

    _abstract = True
    _footprint = dict(
        info = 'AlgoComponent designed to run an S2M experiment without MPI parallelization.',
        attr = dict(
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
            deterministic = dict(
                type     = bool,
                default  = True,
                optional = True,
            ),
        )
    )

    def vortex_task(self, **kwargs):
        rdict = dict(rc=True)
        rundir = self.system.getcwd()
        if self.subdir is not self.system.path.dirname(rundir):
            thisdir = self.system.path.join(rundir, self.subdir)
            with self.system.cdcontext(self.subdir, create=True):
                rdict = self._commons(rundir, thisdir, rdict, **kwargs)

        else:
            thisdir = rundir
            rdict = self._commons(rundir, thisdir, rdict, **kwargs)

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
        if not self.system.path.islink(dest) and not self.system.path.isfile(dest):
            if self.system.path.isfile(local):
                self.system.symlink(local, dest)

    def postfix(self):
        self.system.subtitle('{0:s} : directory listing (post-run)'.format(self.kind))
        for line in self.system.dir():
            print(line)


class GuessWorker(_S2MWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['guess', 'intercep']
            ),
            interpreter = dict(
                values = ['python', 'current']
            ),
            reforecast = dict(
                type     = bool,
                default  = False,
                optional = True,
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
        try:
            self.local_spawn(list_name)
            self.postfix()
        except ExecutionError:
            rdict['rc'] = S2MExecutionError(self.progname, self.deterministic, self.subdir,
                                            self.datebegin, self.dateend)
        finally:
            return rdict  # Note than in the other case return rdict is at the end

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
    """TODO: Class documentation."""

    _abstract = True
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
            ),
            execution = dict(
                values = ['analysis', 'forecast', 'reanalysis', 'reforecast'],
                optional = True,
            ),
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
                self._days[n] = self.get_guess(try_dates, fatal=False)
                d = d + Period(days=1)
        elif ndays == 0:
            logger.warning('The given time period is too short, doing nothing.')
        else:
            logger.warning('datebegin argument must be before dateend argument')
        return self._days

    def _commons(self, rundir, thisdir, rdict, **kwargs):
        _Safran_namelists = ['ANALYSE', 'CENPRAA', 'OBSERVA', 'OBSERVR', 'IMPRESS',
                             'ADAPT', 'SORTIES', 'MELANGE', 'EBAUCHE', 'rsclim.don']
        for nam in _Safran_namelists:
            self.link_ifnotprovided(self.system.path.join(rundir, nam), nam)

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        _OP_files_common = ['OPlisteo', 'OPlysteo', 'OPlistem', 'Oplystem', 'OPlisteml', 'OPlysteml',
                            'OPclim', 'OPNOmt', 'OPsat', 'OPnoir', 'OPposte']
        _OP_files_individual = ['OPguess', 'OPprevi', 'OPMET', 'OPSA', 'OPSG', 'OPSAP', 'OPSAN']
        if self.execution == 'reanalysis':
            # In reanalysis tasks the parallelisation is made over the seasons so
            # the observations are "individal files"
            _OP_files_individual.extend(['OPA', 'OPR', 'OPS', 'OPT'])
            # Add 'weather type' normals
            _OP_files_common.extend(['OPNOot', 'OPNOmt'])
        else:
            _OP_files_common.extend(['OPA', 'OPR', 'OPS', 'OPT'])

        for op_file in _OP_files_common:
            if not self.system.path.isfile(op_file):
                with io.open(op_file, 'w') as f:
                    f.write(rundir.rstrip('/') + '@\n')

        for op_file in _OP_files_individual:
            if not self.system.path.isfile(op_file):
                with io.open(op_file, 'w') as f:
                    f.write(thisdir.rstrip('/') + '@\n')

        self.system.remove('sapfich')

        print('Running task {0:s}'.format(self.kind))
        for day, dates in self.days.items():
            nech = len(dates) if len(dates) == 9 else 5
            self.sapdat(dates[-1], nech)
            rdict = self._safran_task(rundir, thisdir, day, dates, rdict)

        self.postfix()

        return rdict

    def _safran_task(self, rundir, thisdir, rdict):
        """The piece of code specific to a Safran submodule does here."""
        raise NotImplementedError()

    def check_mandatory_resources(self, rdict, filenames):
        outcome = True
        missing_files = False
        for filename in filenames:
            if not self.system.path.exists(filename):
                missing_files = True
        if missing_files:
            if self.execution not in ['reforecast', ]:
                rdict['rc'] = InputCheckerError('Some mandatory flow resources are missing.')
            # In analysis cases (oper or research) missing guess are not fatal since SAFRAN uses
            # a climatological guess that is corrected by the observations
            if self.execution not in ['analysis', 'reanalysis']:
                outcome = False
        return rdict, outcome

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')
            # In reanalysis execution the RR guess comes from a "weather types" analysis
            d.write('0,0,0\n')
            d.write('3,1,3,3\n')

    def get_guess(self, dates, prefix='P', fatal=False, dt=3):
        """Try to guess the corresponding input file."""
        # TODO : Ajouter un control de cohérence sur les cumuls : on ne doit pas
        # mélanger des cumuls sur 6h avec des cumuls sur 24h
        actual_dates = list()
        for date in dates:
            p = 'P{0:s}'.format(date.yymdh)
            if self.system.path.exists(p) and not self.system.path.islink(p):
                actual_dates.append(date)
            elif self.system.path.exists('{0:s}{1:s}'.format(prefix, date.ymdh)):
                self.link_in('{0:s}{1:s}'.format(prefix, date.ymdh), prefix + date.yymdh)
                actual_dates.append(date)
            else:
                if self.system.path.islink(p):
                    self.system.remove(p)
                # We try to find the P file with format Pyymmddhh_tt (yymmddhh + tt = date)
                # The maximum time is 108h (4 days)
                if self.execution == 'reforecast':
                    # We look for the first forecast run before the begining of the target period
                    t = int((date - self.datebegin).days * 24 + (date - self.datebegin).seconds / 3600)
                elif self.execution == 'forecast':
                    # In operational task the datebegin is 24h earlier (pseudo-forecast from 6h J-1 to 6h J)
                    # The forecast perdiod is split into two parts :
                    #     1) From J-1 6h to J 6h
                    #        The 'deterministic member' takes the 6h ARPEGE analysis
                    #        All PEARP members take the forecasts from the 6h J lead time
                    #     2) From J 6h to J+4 6h
                    #        The deterministic member takes the forecasts from the 0h J lead time
                    #        All PEARP members take the forecats froms the 18h J-1 lead time
                    d = date - Period(hours=6)
                    oldp = 'P{0:s}_{1!s}'.format(d.yymdh, 6)
                    if self.system.path.exists(oldp):
                        self.link_in(oldp, p)
                        actual_dates.append(date)
                    else:
                        if dates[0] == self.datebegin:
                            t = int((date - self.datebegin).days * 24 +
                                    (date - self.datebegin).seconds / 3600)
                        else:
                            t = int((date - self.datebegin).days * 24 +
                                    (date - self.datebegin).seconds / 3600) - 18
                else:
                    if date == dates[-1]:
                        # Avoid to take the first P file of the next day
                        # Check for a 6-hour analysis
                        d = date - Period(hours=6)
                        oldp = 'P{0:s}_{1!s}'.format(d.yymdh, 6)
                        if self.system.path.exists(oldp):
                            self.link_in(oldp, p)
                            actual_dates.append(date)
                        else:
                            # If there is no 6-hour analysis we need at least a 24h forecast
                            # to have a cumulate rr24
                            t = 24
                    else:
                        t = 0
                while not self.system.path.islink(p) and (t <= 108):
                    d = date - Period(hours=t)
                    oldp = 'P{0:s}_{1!s}'.format(d.yymdh, t)
                    if self.system.path.exists(oldp):
                        self.link_in(oldp, p)
                        actual_dates.append(date)
                    t = t + dt  # 3-hours check

        if 5 < len(actual_dates) < 9:
            # We must have either 5 or 9 dates, if not we only keep synoptic ones
            for date in actual_dates:
                if date.hour not in [0, 6, 12, 18]:
                    actual_dates.remove(date)
        if len(actual_dates) < 5:
            # print("WARNING : Not enough guess for date {0:s}, expecting at least 5, "
            #      "got {1:d}".format(dates[0].ymdh, len(actual_dates)))
            # In this case, actual_dates is filled with the mandatory dates
            if prefix == 'P':
                actual_dates = self.get_guess(dates, prefix='E', fatal=False)
            else:
                logger.warning('No guess files found for date {0:s}, ' + 
                               'SAFRAN will run with climatological guess'.format(date.ymdh))
                actual_dates = [d for d in dates if d.hour in [0, 6, 12, 18]]

        return actual_dates


class InterCEPWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['intercep']
            ),
        )
    )

    def _commons(self, rundir, thisdir, rdict, **kwargs):
        _Safran_namelists = ['ANALYSE', 'CENPRAA', 'OBSERVA', 'OBSERVR', 'IMPRESS',
                             'ADAPT', 'SORTIES', 'MELANGE', 'EBAUCHE', 'surfz']
        for nam in _Safran_namelists:
            self.link_in(self.system.path.join(rundir, nam), nam)

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        _OP_files_individual = ['OPguess']
        _OP_files_common = ['OPcep']

        for op_file in _OP_files_individual:
            if not self.system.path.isfile(op_file):
                with io.open(op_file, 'w') as f:
                    f.write(thisdir + '@\n')

        for op_file in _OP_files_common:
            if not self.system.path.isfile(op_file):
                with io.open(op_file, 'w') as f:
                    f.write(rundir + '@\n')

        if self.datebegin < Date(2002, 8, 1):
            print('Running task {0:s}'.format(self.kind))
            rundate = self.datebegin.replace(hour=self.day_begins_at)
            while rundate <= self.dateend and rundate < Date(2002, 8, 1):
                self.sapdat(rundate)
                list_name = self.system.path.join(thisdir, self.kind + rundate.ymdh + '.out')
                self.local_spawn(list_name)
                rundate = rundate + Period(hours=6)
        else:
            print('Guess should already be there, doing nothing')

        self.postfix()

        return rdict

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')


class SafraneWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['safrane']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        nech = len(dates) if len(dates) == 9 else 5
        self.get_guess(dates)
        mandatory_dates = [d for d in dates if d.hour in [0, 6, 12, 18]]
        rdict, go = self.check_mandatory_resources(rdict, ['P{0:s}'.format(d.yymdh)
                                                           for d in mandatory_dates])
        if go:
            for d in dates:
                logger.info('Running date : {0:s}'.format(d.ymdh))
                self.sapdat(d, nech)
                # Creation of the 'sapfich' file containing the name of the output file
                with io.open('sapfich', 'w') as f:
                    f.write('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh))
                list_name = self.system.path.join(thisdir, self.kind + d.ymdh + '.out')
                try:
                    self.local_spawn(list_name)
                    # Reanalysis : if the execution was allright we don't need the log file
                    # if self.execution in ['reanalysis', 'reforecast']:
                    #     self.system.remove(list_name)
                except ExecutionError:
                    self.system.remove('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh))
                    rdict['rc'] = S2MExecutionError(self.progname, self.deterministic,
                                                    self.subdir,
                                                    self.datebegin, self.dateend)
        return rdict


class SypluieWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sypluie']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5_ARP')
        # Creation of the 'sapfich' file containing the name of the output file
        with io.open('sapfich', 'w') as f:
            f.write('SAPLUI5' + dates[-1].ymdh)
        list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
        try:
            self.local_spawn(list_name)
            # Reanalysis : if the execution was allright we don't need the log file
            # if self.execution in ['reanalysis', 'reforecast']:
            #     self.system.remove(list_name)
        except ExecutionError:
            self.system.remove('SAPLUI5' + dates[-1].ymdh)
            rdict['rc'] = S2MExecutionError(self.progname, self.deterministic, self.subdir,
                                            self.datebegin, self.dateend)
        finally:
            return rdict  # Note than in the other case return rdict is at the end

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')
            # In reanalysis execution the RR guess comes from a "weather types" analysis
            # Except for more recent years for which ARPEGE rr guess are available
            if self.execution == 'reanalysis' and self.datebegin < Date(2017, 8, 1, 0):
                d.write('0,0,1\n')
            else:
                d.write('0,0,3\n')
            d.write('3,1,3,3\n')


class SyrpluieWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrpluie']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        self.get_guess(dates)
        # Creation of the 'sapfich' file containing the name of the output file
        with io.open('sapfich', 'w') as f:
            f.write('SAPLUI5' + dates[-1].ymdh)
        list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
        mandatory_dates = [d for d in dates if d.hour in [0, 6, 12, 18]]
        rdict, go = self.check_mandatory_resources(rdict, ['P{0:s}'.format(d.yymdh)
                                                           for d in mandatory_dates])
        if go:
            try:
                self.local_spawn(list_name)
                # Reanalysis : if the execution was allright we don't need the log file
                # if self.execution in ['reanalysis', 'reforecast']:
                #     self.system.remove(list_name)
            except ExecutionError:
                self.system.remove('SAPLUI5' + dates[-1].ymdh)
                rdict['rc'] = S2MExecutionError(self.progname, self.deterministic, self.subdir,
                                                self.datebegin, self.dateend)
            finally:
                return rdict  # Note than in the other case return rdict is at the end
        else:
            return rdict  # Note than in the other case return rdict is at the end

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')
            # In reanalysis execution the RR guess comes from a "weather types" analysis
            # Except for more recent years for which ARPEGE rr guess are available
            if self.execution == 'reanalysis'and self.datebegin < Date(2017, 8, 1, 0):
                d.write('0,0,1\n')
            else:
                d.write('0,0,3\n')
            d.write('3,1,3,3\n')


class SyvaprWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syvapr']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        rdict, go = self.check_mandatory_resources(rdict, ['SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh) for d in dates])
        if go:
            for j, d in enumerate(dates):
                self.link_in('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh), 'SAFRAN' + six.text_type(j + 1))
            self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5')
            list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
            try:
                self.local_spawn(list_name)
                # Reanalysis : if the execution was allright we don't need the log file
                # if self.execution in ['reanalysis', 'reforecast']:
                #     self.system.remove(list_name)
                for suffix in ['HA', 'HS', 'NA', 'TA', 'TS', 'UA', 'US', 'VA', 'VS']:
                    self.mv_if_exists('SAF4D_{0:s}'.format(suffix),
                                      'SAF4D_{0:s}_{1:s}'.format(suffix, dates[-1].ymdh))
            except ExecutionError:
                rdict['rc'] = S2MExecutionError(self.progname, False, self.subdir,
                                                self.datebegin, self.dateend)

        return rdict  # Note than in the other case return rdict is at the end


class SyvafiWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syvafi']
            ),
            deterministic = dict(
                default  = False,
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        # if self.check_mandatory_resources(rdict, ['SAPLUI5' + six.text_type(day), ]):
        for j, d in enumerate(dates):
            self.link_in('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh), 'SAFRAN' + six.text_type(j + 1))
        self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5')
        for suffix in ['HA', 'HS', 'NA', 'TA', 'TS', 'UA', 'US', 'VA', 'VS']:
            self.link_in('SAF4D_{0:s}_{1:s}'.format(suffix, dates[-1].ymdh), 'SAF4D_{0:s}'.format(suffix))
        list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
        try:
            self.local_spawn(list_name)
            self.mv_if_exists('fort.90', 'TAL' + dates[-1].ymdh)
            # if self.execution in ['reanalysis', 'reforecast']:
            #     self.system.remove(list_name)
        except ExecutionError:
            rdict['rc'] = S2MExecutionError(self.progname, False, self.subdir,
                                            self.datebegin, self.dateend)

        return rdict


class SyrmrrWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrmrr']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, day, dates, rdict):

        rdict, go = self.check_mandatory_resources(rdict, ['SAPLUI5' + dates[-1].ymdh])
        if go:
            self.link_in('SAPLUI5' + dates[-1].ymdh, 'fort.12')
            list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
            try:
                self.local_spawn(list_name)
                self.mv_if_exists('fort.13', 'SAPLUI5' + dates[-1].ymdh)
                self.mv_if_exists('fort.14', 'SAPLUI5_ARP' + dates[-1].ymdh)
                self.mv_if_exists('fort.15', 'SAPLUI5_ANA' + dates[-1].ymdh)
                # if self.execution in ['reanalysis', 'reforecast']:
                #     self.system.remove(list_name)
            except ExecutionError:
                rdict['rc'] = S2MExecutionError(self.progname, self.deterministic, self.subdir,
                                                self.datebegin, self.dateend)

        return rdict


class SytistWorker(_SafranWorker):
    """TODO: Class documentation."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sytist']
            ),
            metadata = dict(
                values   = ['StandardSAFRAN', 'StandardPROSNOW'],
                optional = True,
            ),
        )
    )

    def postfix(self, rdict):
        if self.metadata:
            for f in ['FORCING_massif.nc', 'FORCING_postes.nc']:
                if self.system.path.isfile(f):
                    forcing_to_modify = getattr(S2M_standard_file, self.metadata)(f, "a")
                    forcing_to_modify.GlobalAttributes()
                    forcing_to_modify.add_standard_names()
                    forcing_to_modify.close()

        if 'rc' in rdict.keys() and isinstance(rdict['rc'], S2MExecutionError):
            self.system.remove('FORCING_massif.nc')
            self.system.remove('FORCING_postes.nc')

        self.mv_if_exists('FORCING_massif.nc',
                          'FORCING_massif_{0:s}_{1:s}.nc'.format(self.datebegin.ymd6h, self.dateend.ymd6h))
        self.mv_if_exists('FORCING_postes.nc',
                          'FORCING_postes_{0:s}_{1:s}.nc'.format(self.datebegin.ymd6h, self.dateend.ymd6h))

        if self.execution in ['analysis', 'reanalysis']:
            self.system.tar('liste_obs_{0:s}_{1:s}.tar'.format(self.datebegin.ymd6h, self.dateend.ymd6h), 'liste_obs*')

        super(SytistWorker, self).postfix()

    def _commons(self, rundir, thisdir, rdict, **kwargs):
        self.system.remove('sapfich')
        print('Running task {0:s}'.format(self.kind))
        for day, dates in self.days.items():
            nech = len(dates) if len(dates) == 9 else 5
            self.sapdat(dates[-1], nech)
            rdict = self._safran_task(rundir, thisdir, day, dates, rdict)

        self.postfix(rdict)
        return rdict

    def _safran_task(self, rundir, thisdir, day, dates, rdict):
        self.link_in('SAPLUI5' + dates[-1].ymdh, 'SAPLUI5')
        self.link_in('SAPLUI5_ARP' + dates[-1].ymdh, 'SAPLUI5_ARP')
        self.link_in('SAPLUI5_ANA' + dates[-1].ymdh, 'SAPLUI5_ANA')
        for suffix in ['HA', 'HS', 'NA', 'TA', 'TS', 'UA', 'US', 'VA', 'VS']:
            self.link_in('SAF4D_{0:s}_{1:s}'.format(suffix, dates[-1].ymdh), 'SAF4D_{0:s}'.format(suffix))
        rdict, go = self.check_mandatory_resources(rdict,
                                                   ['SAPLUI5'] + ['SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh)
                                                                  for d in dates])
        if go:
            for j, d in enumerate(dates):
                self.link_in('SAFRANE_d{0!s}_{1:s}'.format(day, d.ymdh), 'SAFRAN' + six.text_type(j + 1))
            list_name = self.system.path.join(thisdir, self.kind + dates[-1].ymd + '.out')
            try:
                self.local_spawn(list_name)
            except ExecutionError:
                rdict['rc'] = S2MExecutionError(self.progname, self.deterministic, self.subdir,
                                                self.datebegin, self.dateend)

        return rdict

    def sapdat(self, thisdate, nech=5):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        self.system.remove('sapdat')

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with io.open('sapdat', 'w') as d:
            d.write(thisdate.strftime('%y,%m,%d,%H,') + six.text_type(nech) + '\n')
            if self.execution in ['forecast', 'reforecast']:
                d.write('0,0,0\n')
            elif self.execution in ['analysis', 'reanalysis']:
                d.write('0,1,0\n')
            d.write('3,1,3,3\n')
            d.write('0\n')
            d.write('1,1,{0!s}\n'.format(self.posts))


class S2MExecutionError(ExecutionError):
    """TODO: Class documentation."""

    def __init__(self, model, deterministic, subdir, datebegin, dateend):
        self.model = model
        self.deterministic = deterministic  # Key used for delayed exception management
        self.subdir = subdir
        self.datebegin = datebegin
        self.dateend = dateend
        super(S2MExecutionError, self).__init__(self.model + ' execution failed.')

    def __str__(self):
        return ("Error while running " + self.model + " for member " + self.subdir + " for period " +
                self.datebegin.ymdh + " - " + self.dateend.ymdh)

    def __reduce__(self):
        red = list(super(S2MExecutionError, self).__reduce__())
        red[1] = tuple([self.model, self.deterministic, self.subdir, self.datebegin,
                        self.dateend])  # Les arguments qui seront passes a __init__
        return tuple(red)


@echecker.disabled_if_unavailable
class SurfexWorker(_S2MWorker):
    """This algo component is designed to run a SURFEX experiment without MPI parallelization."""

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
            ),
            dailynamelist = dict(
                info = "If daily is True, possibility to provide a list of namelists to change each day",
                type = list,
                optional = True,
                default = [],
            ),
        )
    )

    def modify_prep(self, datebegin_this_run):
        """
        The PREP file needs to be modified if the init date differs from the starting
        date or if a threshold needs to be applied on snow water equivalent.
        """
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

        if len(self.dailynamelist) > 1:
            list_files_copy = self.dailynamelist
        else:
            list_files_copy = ["OPTIONS.nam"]
        list_files_link = ["PGD.nc", "METADATA.xml", "ecoclimapI_covers_param.bin",
                           "ecoclimapII_eu_covers_param.bin", "drdt_bst_fit_60.nc"]
        list_files_link_ifnotprovided = ["PREP.nc"]

        for required_copy in list_files_copy:
            self.copy_if_exists(self.system.path.join(rundir, required_copy), required_copy)
        for required_link in list_files_link:
            self.link_in(self.system.path.join(rundir, required_link), required_link)
        for required_link in list_files_link_ifnotprovided:
            self.link_ifnotprovided(self.system.path.join(rundir, required_link), required_link)
            # For reforecast:
            self.link_ifnotprovided(self.system.path.join(self.system.path.dirname(thisdir), required_link),
                                    required_link)

        rdict = self._surfex_task(rundir, thisdir, rdict)
        self.postfix()
        return rdict

    def _surfex_task(self, rundir, thisdir, rdict):
        # ESCROC cases: each member will need to have its own namelist
        # meteo ensemble cases: the forcing modification must be applied to all members and the namelist
        # generation requires that the forcing generation has already be done. Therefore, preprocessing
        # is done in the offline algo in all these cases
        # Determinstic cases : the namelist is prepared in the preprocess algo component in order to allow
        # to build PGD and PREP
        namelist_ready = self.kind == 'deterministic'
        need_other_run = True
        need_other_forcing = True
        need_save_forcing = False
        updateloc = True
        datebegin_this_run = self.datebegin

        sytron = self.kind == "ensmeteo+sytron" and self.subdir == "mb036"

        changenamelistdaily = self.daily and (len(self.dailynamelist) > 1)

        while need_other_run:

            # Modification of the PREP file
            self.modify_prep(datebegin_this_run)

            if need_other_forcing:

                if self.kind == "escroc":
                    # ESCROC only: the forcing files are in the father directory (same forcing for all members)
                    forcingdir = rundir
                elif sytron:
                    # ensmeteo+sytron: the forcing files are supposed to be in the subdirectories
                    # of each member except for the sytron member
                    forcingdir = rundir + "/mb035"
                else:
                    # ensmeteo or ensmeteo+escroc: the forcing files are supposed to be in the subdirectories
                    # of each member
                    # determinstic case: the forcing file(s) is/are in the only directory
                    forcingdir = thisdir

                if len(self.geometry) > 1:
                    print("FORCING AGGREGATION")
                    forcinglist = []
                    for massif in self.geometry:
                        dateforcbegin, dateforcend = get_file_period(
                            "FORCING",
                            forcingdir + "/" + massif,
                            datebegin_this_run,
                            self.dateend)
                        forcingname = "FORCING_" + massif + ".nc"
                        self.system.mv("FORCING.nc", forcingname)
                        forcinglist.append(forcingname)

                    print(forcinglist)
                    try:
                        forcinput_applymask(forcinglist, "FORCING.nc")
                    except TimeListException:
                        deterministic = self.subdir == "mb035"
                        rdict['rc'] = S2MExecutionError("merge of forcings", deterministic, self.subdir,
                                                        dateforcbegin, dateforcend)
                        return rdict  # Note than in the other case return rdict is at the end

                    need_save_forcing = True
                else:
                    # Get the first file covering part of the whole simulation period
                    print("LOOK FOR FORCING")
                    dateforcbegin, dateforcend = get_file_period(
                        "FORCING",
                        forcingdir,
                        datebegin_this_run,
                        self.dateend)
                    print("FORCING FOUND")

                    if self.geometry[0] in ["alp", "pyr", "cor"]:
                        print("FORCING EXTENSION")
                        liste_massifs = infomassifs().dicArea[self.geometry[0]]
                        liste_aspect = infomassifs().get_list_aspect(8, ["0", "20", "40"])
                        self.mv_if_exists("FORCING.nc", "FORCING_OLD.nc")
                        forcinput_select('FORCING_OLD.nc', 'FORCING.nc', liste_massifs, 0, 5000,
                                         ["0", "20", "40"], liste_aspect)
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
                    newcontent = update_surfex_namelist_object(
                        namelist.contents,
                        datebegin_this_run,
                        dateend=dateend_this_run,
                        updateloc=updateloc,
                        physicaloptions=self.physical_options,
                        snowparameters=self.snow_parameters)
                    newnam = footprints.proxy.container(filename=namelist.container.basename)
                    newcontent.rewrite(newnam)
                    newnam.close()
                if self.daily:
                    updateloc = True
                else:
                    namelist_ready = True

            if changenamelistdaily:
                # Change the namelist
                self.link_in(self.dailynamelist.pop(0), "OPTIONS.nam")

            # Run surfex offline
            list_name = self.system.path.join(thisdir, 'offline.out')

            try:
                self.local_spawn(list_name)
                # Uncomment these lines to test the behaviour in case of failure of 1 member
                # if self.subdir == "mb006":
                #     deterministic = self.subdir == "mb035"
                #     print("DEBUGINFO")
                #     print(dir(self))
                #     rdict['rc'] = S2MExecutionError(self.progname, deterministic,
                #                                     self.subdir, datebegin_this_run, dateend_this_run)

            except ExecutionError:
                deterministic = self.subdir == "mb035"
                rdict['rc'] = S2MExecutionError(self.progname, deterministic, self.subdir,
                                                datebegin_this_run, dateend_this_run)
                return rdict  # Note than in the other case return rdict is at the end

            # Copy the SURFOUT file for next iteration
            self.system.cp("SURFOUT.nc", "PREP.nc")

            # Post-process
            pro = massif_simu("ISBA_PROGNOSTIC.OUT.nc", openmode='a')
            pro.massif_natural_risk()
            pro.dataset.GlobalAttributes()
            pro.dataset.add_standard_names()
            pro.close()

            # Rename outputs with the dates
            save_file_date(".", "SURFOUT", dateend_this_run, newprefix="PREP")
            save_file_period(".", "ISBA_PROGNOSTIC.OUT", datebegin_this_run, dateend_this_run,
                             newprefix="PRO")

            # Prepare next iteration if needed
            datebegin_this_run = dateend_this_run
            need_other_run = dateend_this_run < self.dateend

            print(dateend_this_run, self.dateend)
            print("INFO SAVE FORCING", need_save_forcing, need_other_run, need_other_forcing)

            if need_save_forcing and not (need_other_run and not need_other_forcing):
                save_file_period(".", "FORCING", dateforcbegin, dateforcend)
            # Remove the symbolic link for next iteration (not needed since now we rename the forcing just before
#             self.system.remove("FORCING.nc")

        return rdict


@echecker.disabled_if_unavailable
class PrepareForcingWorker(TaylorVortexWorker):
    """This algo component is designed to run a SURFEX experiment without MPI parallelization."""

    _footprint = dict(
        info = 'AlgoComponent designed to run a SURFEX experiment without MPI parallelization.',
        attr = dict(
            datebegin = a_date,
            dateend   = a_date,
            kind = dict(
                values = ['prepareforcing'],
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = False
            ),
            geometry_in = dict(
                info = "Area information in case of an execution on a massif geometry",
                type = footprints.stdtypes.FPList,
                optional = True,
                default = None
            ),
            geometry_out = dict(
                info = "The resource's massif geometry.",
                type = str,
            )
        )
    )

    def vortex_task(self, **kwargs):
        rdict = dict(rc=True)
        rundir = self.system.getcwd()
        if self.subdir is not self.system.path.dirname(rundir):
            thisdir = self.system.path.join(rundir, self.subdir)
            with self.system.cdcontext(self.subdir, create=True):
                rdict = self._commons(rundir, thisdir, rdict, **kwargs)

        else:
            thisdir = rundir
            rdict = self._commons(rundir, thisdir, rdict, **kwargs)

        return rdict

    def _commons(self, rundir, thisdir, rdict, **kwargs):

        rdict = self._prepare_forcing_task(rundir, thisdir, rdict)
        self.postfix()

        return rdict

    def _prepare_forcing_task(self, rundir, thisdir, rdict):

        need_other_run = True
        need_other_forcing = True
        need_save_forcing = False
        datebegin_this_run = self.datebegin

        while need_other_run:

            if need_other_forcing:

                forcingdir = rundir

                if len(self.geometry_in) > 1:
                    print("FORCING AGGREGATION")
                    forcinglist = []
                    for massif in self.geometry_in:
                        dateforcbegin, dateforcend = get_file_period("FORCING", forcingdir + "/" + massif,
                                                                     datebegin_this_run, self.dateend)
                        forcingname = "FORCING_" + massif + ".nc"
                        self.system.mv("FORCING.nc", forcingname)
                        forcinglist.append(forcingname)

                    forcinput_applymask(forcinglist, "FORCING.nc", )
                    need_save_forcing = True
                else:
                    # Get the first file covering part of the whole simulation period
                    print("LOOK FOR FORCING")
                    dateforcbegin, dateforcend = get_file_period("FORCING", forcingdir,
                                                                 datebegin_this_run, self.dateend)
                    print("FORCING FOUND")

                    if self.geometry_in[0] in ["alp", "pyr", "cor"]:
                        if "allslopes" in self.geometry_out:
                            list_slopes = ["0", "20", "40"]
                        elif "flat" in self.geometry_out:
                            list_slopes = ["0"]

                        print("FORCING EXTENSION")
                        liste_massifs = infomassifs().dicArea[self.geometry_in[0]]
                        liste_aspect = infomassifs().get_list_aspect(8, list_slopes)
                        self.system.mv("FORCING.nc", "FORCING_OLD.nc")
                        forcinput_select('FORCING_OLD.nc', 'FORCING.nc', liste_massifs,
                                         0, 5000, list_slopes, liste_aspect)
                        need_save_forcing = True

            dateend_this_run = min(self.dateend, dateforcend)

            # Prepare next iteration if needed
            datebegin_this_run = dateend_this_run
            need_other_run = dateend_this_run < self.dateend

            if need_save_forcing and not (need_other_run and not need_other_forcing):
                save_file_period(rundir, "FORCING", dateforcbegin, dateforcend)

        return rdict

    def postfix(self):
        self.system.subtitle('{0:s} : directory listing (post-run)'.format(self.kind))
        for line in self.system.dir():
            print(line)


class Guess(ParaExpresso):
    """AlgoComponent that runs several executions of a guess-making script."""

    _footprint = dict(
        info = 'AlgoComponent that runs several executions of a guess-making script',
        attr = dict(
            kind = dict(
                values = ['guess'],
            ),
            interpreter = dict(
                values = ['python', 'current']
            ),
            reforecast = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Guess, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super(Guess, self)._default_common_instructions(rh, opts)
        ddict['interpreter'] = self.interpreter
        ddict['reforecast'] = self.reforecast
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Note: The number of members and the name of the subdirectories could be
        # auto-detected using the sequence
        cpl_model = self.get_origin(rh, opts)
        subdirs = self.get_subdirs(rh, opts)
        self._add_instructions(common_i, dict(subdir=subdirs, deterministic=cpl_model))
        self._default_post_execute(rh, opts)

    def get_subdirs(self, rh, opts):
        """Get the subdirectories from the effective inputs"""
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = list()
        for am in avail_members:
            if am.rh.container.dirname not in subdirs:
                subdirs.append(am.rh.container.dirname)

        return subdirs

    def get_origin(self, rh, opts):
        """Get the subdirectories from the effective inputs"""
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = list()
        cpl_model = list()
        for am in avail_members:
            if am.rh.container.dirname not in subdirs:
                subdirs.append(am.rh.container.dirname)
                cpl_model.append(am.rh.provider.vconf == '4dvarfr')

        return cpl_model

    def role_ref_namebuilder(self):
        return 'Gridpoint'

    def postfix(self, rh, opts):
        pass


class S2MComponent(ParaBlindRun):
    """AlgoComponent that runs several executions in parallel."""

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values   = ['safrane', 'syrpluie', 'syrmrr', 'sytist', 'sypluie', 'syvapr',
                            'syvafi', 'intercep'],
            ),
            engine = dict(
                values   = ['s2m']
            ),
            datebegin = a_date,
            dateend   = a_date,
            execution = dict(
                values   = ['analysis', 'forecast'],
                optional = True,
            ),
            metadata = dict(
                values   = ['StandardSAFRAN', 'StandardPROSNOW'],
                optional = True,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(S2MComponent, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
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
        cpl_model = self.get_origin(rh, opts)
        subdirs = self.get_subdirs(rh, opts)
        self._add_instructions(common_i, dict(subdir=subdirs, deterministic=cpl_model))
        self._default_post_execute(rh, opts)

    def postfix(self, rh, opts):
        pass

    def get_subdirs(self, rh, opts):
        """Get the subdirectories from the effective inputs"""
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = list()
        for am in avail_members:
            if am.rh.container.dirname not in subdirs:
                subdirs.append(am.rh.container.dirname)
# Ca partait d'une bonne idée mais en pratique il y a plein de cas particuliers pour lesquels ça pose problème
# reanalyse safran, surfex postes, etc
#         self.algoassert(len(set(subdirs)) == len(set([am.rh.provider.member for am in avail_members])))

        # Crash if subdirs is an empty list (it means that there is not any input available)
        self.algoassert(len(subdirs) >= 1)
        return subdirs

    def get_origin(self, rh, opts):
        """Get the subdirectories from the effective inputs"""
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = list()
        cpl_model = list()
        for am in avail_members:
            if am.rh.container.dirname not in subdirs:
                subdirs.append(am.rh.container.dirname)
                if 'source_conf' in dir(am.rh.resource):
                    cpl_model.append(am.rh.resource.source_conf == '4dvarfr')
                else:
                    # If the origin of the guess is not given the execution is in
                    # 'deterministic' mode (monthly reanalysis)
                    cpl_model.append(True)

        return cpl_model

    def role_ref_namebuilder(self):
        return 'Ebauche'


class S2MReanalysis(S2MComponent):
    """AlgoComponent that runs several executions in parallel."""

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            execution = dict(
                values   = ['reanalysis'],
                optional = False,
            ),
        ),
    )

    def role_ref_namebuilder(self):
        return 'Observations'

    def get_subdirs(self, rh, opts):
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = [am.rh.container.dirname for am in avail_members]
        return list(set(subdirs))

    def get_list_seasons(self, rh, opts):
        list_dates_begin_input = list()
        list_dates_end_input = list()

        datebegin_input = self.datebegin
        if self.datebegin.month >= 8:
            dateend_input = min(Date(self.datebegin.year + 1, 8, 1, 6, 0, 0), self.dateend)
        else:
            dateend_input = min(Date(self.datebegin.year, 8, 1, 6, 0, 0), self.dateend)

        list_dates_begin_input.append(datebegin_input)
        list_dates_end_input.append(dateend_input)

        while dateend_input < self.dateend:
            datebegin_input = dateend_input
            dateend_input = min(datebegin_input.replace(year=datebegin_input.year + 1), self.dateend)
            list_dates_begin_input.append(datebegin_input)
            list_dates_end_input.append(dateend_input)

        list_dates_begin_input.sort()
        list_dates_end_input.sort()

        return list_dates_begin_input, list_dates_end_input

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super(S2MComponent, self)._default_common_instructions(rh, opts)

        for attribute in self.footprint_attributes:
            if attribute not in ['datebegin', 'dateend']:
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
        deterministic = [True] * len(subdirs)
        subdirs.sort()
        list_dates_begin, list_dates_end = self.get_list_seasons(rh, opts)
        self._add_instructions(common_i, dict(subdir=subdirs,
                                              datebegin=list_dates_begin,
                                              dateend=list_dates_end,
                                              deterministic=deterministic))
        self._default_post_execute(rh, opts)


class S2MReforecast(S2MComponent):
    """AlgoComponent that runs several executions in parallel."""

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            execution = dict(
                values   = ['reforecast'],
                optional = False,
            ),
        ),
    )

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super(S2MComponent, self)._default_common_instructions(rh, opts)

        for attribute in self.footprint_attributes:
            if attribute not in ['datebegin', 'dateend']:
                ddict[attribute] = getattr(self, attribute)

        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        # Note: The number of members and the name of the subdirectories could be
        # auto-detected using the sequence
        subdirs, list_dates_begin, list_dates_end = self.get_individual_instructions(rh, opts)
        deterministic = [True] * len(subdirs)
        self._add_instructions(common_i, dict(subdir=subdirs,
                                              datebegin=list_dates_begin,
                                              dateend=list_dates_end,
                                              deterministic=deterministic))
        self._default_post_execute(rh, opts)

    def get_individual_instructions(self, rh, opts):
        avail_members = self.context.sequence.effective_inputs(role=self.role_ref_namebuilder())
        subdirs = list()
        list_dates_begin = list()
        list_dates_end = list()
        for am in avail_members:
            if am.rh.container.dirname not in subdirs:
                subdirs.append(am.rh.container.dirname)
                list_dates_begin.append(am.rh.resource.date + Period(hours=12))
                list_dates_end.append(am.rh.resource.date + Period(hours=108))

        return subdirs, list_dates_begin, list_dates_end


@echecker.disabled_if_unavailable
class SurfexComponent(S2MComponent):
    """AlgoComponent that runs several executions in parallel."""

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = ['escroc', 'ensmeteo', 'ensmeteo+sytron', 'ensmeteo+escroc', 'prepareforcing']
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
                values = ["E1", "E2", "Crocus", "E2open"],
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
            ),
            dailynamelist = dict(
                info = "If daily is True, possibility to provide a list of namelists to change each day",
                type = list,
                optional = True,
                default = [],
            ),
            multidates = dict(
                info = "If True, several dates allowed",
                type = bool,
                optional = True,
                default = False,
                values = [False]
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
            self._add_instructions(common_i, dict(subdir=subdirs,
                                                  physical_options=physical_options,
                                                  snow_parameters=snow_parameters))
        else:
            self._add_instructions(common_i, dict(subdir=subdirs))
        self._default_post_execute(rh, opts)

    def get_subdirs(self, rh, opts):
        if self.kind == "escroc":
            return ['mb{0:04d}'.format(m) for m in self.members]
        else:
            subdirs = super(SurfexComponent, self).get_subdirs(rh, opts)

            if len(self.geometry) > 1:
                # In the case of a postes geometry, there are 3 effective inputs with forcing file role
                # (They are concatenated)
                # Therefore it is necessary to reduce subdirs to 1 single element for each member
                subdirs = list(set(map(self.system.path.dirname, subdirs)))

            if self.kind == "ensmeteo+sytron":
                subdirs.append('mb036')
            return subdirs

    def role_ref_namebuilder(self):
        return 'Forcing'


@echecker.disabled_if_unavailable
class PrepareForcingComponent(TaylorRun):
    """AlgoComponent that runs several executions in parallel."""

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = ['prepareforcing']
            ),
            engine = dict(
                values = ['s2m']),
            datebegin = dict(
                info = "The list of begin dates of the forcing files",
                type = footprints.stdtypes.FPList,
            ),
            dateend = dict(
                info = "The list of begin dates of the forcing files",
                type = footprints.stdtypes.FPList,
            ),
            geometry_in = dict(
                info = "Area information in case of an execution on a massif geometry",
                type = footprints.stdtypes.FPList,
                default = None
            ),
            geometry_out = dict(
                info = "The resource's massif geometry.",
                type = str,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(PrepareForcingComponent, self).prepare(rh, opts)
        self.env.DR_HOOK_NOT_MPI = 1

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super(PrepareForcingComponent, self)._default_common_instructions(rh, opts)
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
        self._add_instructions(common_i, dict(subdir=subdirs,
                                              datebegin=self.datebegin,
                                              dateend=self.dateend))
        self._default_post_execute(rh, opts)

    def postfix(self, rh, opts):
        pass

    def get_subdirs(self, rh, opts):
        print(type(self.datebegin))
        print(self.datebegin)

        return [begin.year for begin in self.datebegin]

    def role_ref_namebuilder(self):
        return 'Forcing'


@echecker.disabled_if_unavailable
class SurfexComponentMultiDates(SurfexComponent):
    """AlgoComponent that runs several executions in parallel."""
    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            multidates = dict(
                info = "If True, several dates allowed",
                type = bool,
                values = [True]
            )
        )
    )

    def get_dates(self, subdirs):
        listdatebegin_str = map(self.system.path.dirname, subdirs)

        # Pour l'instant je fais le porc parce que le passage de dateend ne marche pas du tout
        duration = Period(days=4)

        listdatebegin = []
        listdateend = []
        for datebegin_str in listdatebegin_str:
            datebegin = Date(datebegin_str)
            listdatebegin.append(datebegin)
            listdateend.append(datebegin + duration)

        return listdatebegin, listdateend

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        self._default_pre_execute(rh, opts)
        # Update the common instructions

        common_i = self._default_common_instructions(rh, opts)

        subdirs = self.get_subdirs(rh, opts)
        listdatebegin, listdateend = self.get_dates(subdirs)
        listdateinit = listdatebegin[:]

        if self.subensemble:
            escroc = ESCROC_subensembles(self.subensemble, self.members)
            physical_options = escroc.physical_options
            snow_parameters = escroc.snow_parameters
            self._add_instructions(common_i, dict(subdir=subdirs,
                                                  datebegin=listdatebegin,
                                                  dateinit=listdateinit,
                                                  dateend=listdateend,
                                                  physical_options=physical_options,
                                                  snow_parameters=snow_parameters))
        else:
            self._add_instructions(common_i, dict(subdir=subdirs,
                                                  datebegin=listdatebegin,
                                                  dateinit=listdateinit,
                                                  dateend=listdateend))
        self._default_post_execute(rh, opts)

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super(SurfexComponentMultiDates, self)._default_common_instructions(rh, opts)
        ddict.pop('datebegin')
        ddict.pop('dateend')
        ddict.pop('dateinit')

        return ddict
