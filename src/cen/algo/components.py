#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

#: No automatic export
__all__ = []

from collections import defaultdict

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.date import Time
from vortex.syntax.stdattrs import a_date
from vortex.algo.components import ParaBlindRun, ParaExpresso
from vortex.tools.parallelism import VortexWorkerBlindRun

_OP_files_common = dict(alp=['OPlisteo', 'OPlistem', 'OPlisteml', 'OPclim', 'OPNOmt'],
                        pyr=['OPlysteo', 'OPlystem', 'OPlysteml', 'OPclim', 'OPNOmt'],)
_OP_files_individual = ['OPguess', 'OPprevi', 'OPMET', 'OPSA', 'OPSAP', 'OPSAN']


class Grib2SafranWorker(VortexWorkerBlindRun):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'grib2safran', 'pearp2safran' ],
                remap = dict(autoremap = 'first'),
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
        )
    )

    def vortex_task(self, **kw):
        rdict = dict(rc=True)
        if self.subdir is not None:
            with self.system.cdcontext(self.subdir, create=True):
                self.local_spawn('stdout.listing')
        else:
            self.local_spawn('stdout.listing')
        return rdict


class SafranWorker(VortexWorkerBlindRun):

    _abstract  = True
    _footprint = dict(
        attr = dict(
            date = a_date,
            terms = dict(
                type = footprints.FPList,
            ),
            vconf = dict(),
            day_begins_at = dict(
                type = int,
                default = 6
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(SafranWorker, self).__init__(*kargs, **kwargs)
        self._actual_terms = None
        self._days = None

    @property
    def actual_terms(self):
        if self._actual_terms is None:
            self._actual_terms = sorted([Time(t) for t in self.terms])
        return self._actual_terms

    @property
    def days(self):
        """Guess the number of days that are to be covered by the forecast"""

        # Compute the days dictionary only once
        if self._days is None:
            new_terms = list(self.actual_terms)  # copy the actual_terms array
            new_dates = [self.date + t for t in new_terms]
            # Ensure that the first term is at the appropriate time
            while new_dates and new_dates[0].hour != self.day_begins_at:
                del new_terms[0]
                del new_dates[0]

            self._days = defaultdict(list)
            for date, term in zip(new_dates, new_terms):
                length = (date - new_dates[0]).length  # duration in seconds since the beginning
                current_day = length // 86400
                # Assign the term to the current
                self._days[current_day + 1].append(term)
                # If the term is exactly the upper bound of the previous day, save it
                if current_day > 0 and length % 86400 == 0:
                    self._days[current_day].append(term)

            if not len(self._days):
                logger.warning('No terms to process, doing nothing.')

        return self._days

    def vortex_task(self, **kw):
        rdict = dict(rc=True)
        rundir = self.system.getcwd()

        if self.subdir is not None:
            thisdir = self.system.path.join(rundir, self.subdir)
            with self.system.cdcontext(self.subdir, create=True):
                self._safran_commons(rundir, thisdir, rdict)
        else:
            thisdir = rundir
            self._safran_commons(rundir, thisdir, rdict)

        return rdict

    def _safran_commons(self, rundir, thisdir, rdict):
        if not self.system.path.exists('SORTIES'):
            self.system.symlink(self.system.path.join(rundir, 'SORTIES'), 'SORTIES')
        if not self.system.path.exists('MELANGE'):
            self.system.symlink(self.system.path.join(rundir, 'MELANGE'), 'MELANGE')

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        for op_file in _OP_files_common[self.vconf]:
            with open(op_file, 'w') as f:
                f.write(rundir + '@\n')

        for op_file in _OP_files_individual:
            with open(op_file, 'w') as f:
                f.write(thisdir + '@\n')

        self.system.remove('sapfich')

        self._safran_task(self, rundir, thisdir, rdict)

    def _safran_task(self, rundir, thisdir, rdict, days):
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

    def mv_if_exists(self, local, dest):
        """Move a file if it exists (intended to deal with output files)."""
        if self.system.path.isfile(local):
            self.system.mv(local, dest)

    def link_in(self, local, dest):
        """Link a file (the target is cleaned first)."""
        self.system.remove(dest)
        self.system.symlink(local, dest)

    def sapdat(self, term):
        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
        sapdat = 'sapdat'
        self.system.remove(sapdat)

        # A PASSER EN NAMELIST OU A PARAMETRISER POUR D'AUTRES APPLICATIONS
        with open(sapdat, 'w') as d:
            d.write((self.date + term).strftime('%y,%m,%d,%H\n'))
            d.write('0,0,0\n')
            d.write('3,1,3,3\n')
            d.write('0\n')
            d.write('1,1,0,0,1\n')


class SafraneWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['safrane']
            ),
        )
    )

    def _safran_task(self, rundir, thisdir, rdict):
        for term in self.actual_terms:
            logger.info('Running term : %s', str(term))
            self.sapdat(term)
            # Creation of the 'sapfich' file containing the name of the output file
            with open('sapfich', 'w') as f:
                f.write('SAF' + str(term.hour))
            list_name = self.system.path.join(thisdir, 'listsaf' + str(term.hour))
            self.local_spawn(list_name)


class SyrpluieWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrpluie']
            ),
        )
    )

    def safran_task(self, rundir, thisdir, rdict):
        for day, dterms in self.days.items():
            logger.info('Running day : %s', str(day))
            self.sapdat(dterms[-1])
            list_name = self.system.path.join(self.thisdir, 'listpluie' + str(day))
            self.local_spawn(list_name)
            self.mv_if_exists('fort.21', 'SAPLUI5' + str(day))


class SyrmrrWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrmrr']
            ),
        )
    )

    def safran_task(self, rundir, thisdir, rdict):
        for day, dterms in self.days.items():
            logger.info('Running day : %s', str(day))
            if self.check_mandatory_resources(rdict, ['SAPLUI5' + str(day), ]):
                self.link_in('SAPLUI5' + str(day), 'fort.12')
                self.sapdat(dterms[-1])
                list_name = self.system.path.join(self.thisdir, 'listrr' + str(day))
                self.local_spawn(list_name)
                self.mv_if_exists('fort.13', 'SAPLUI5' + str(day))
                self.mv_if_exists('fort.14', 'SAPLUI5_ARP' + str(day))
                self.mv_if_exists('fort.15', 'SAPLUI5_ANA' + str(day))


class SytistWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sytist']
            ),
        )
    )

    def safran_task(self, rundir, thisdir, rdict):
        for day, dterms in self.days.items():
            logger.info('Running day : %s', str(day))
            if self.check_mandatory_resources(rdict, ['SAPLUI5' + str(day),
                                                      'SAPLUI5_ARP' + str(day),
                                                      'SAPLUI5_ANA' + str(day)
                                                      ] +
                                                     ['SAF' + str(t) for t in dterms]):
                self.link_in('SAPLUI5' + str(day), 'SAPLUI5')
                self.link_in('SAPLUI5_ARP' + str(day), 'SAPLUI5_ARP')
                self.link_in('SAPLUI5_ANA' + str(day), 'SAPLUI5_ANA')
                for i, term in enumerate(dterms):
                    self.link_in('SAF' + str(term.hour), 'SAFRAN' + str(i + 1))
                self.sapdat(dterms[-1])
                list_name = self.system.path.join(self.thisdir, 'listist' + str(day))
                self.local_spawn(list_name)


class Grib2Safran(ParaExpresso):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = [ 'grib2safran', 'pearp2safran' ],
                remap = dict(autoremap = 'first'),
            ),
            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = True
            ),
        )
    )

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


class Safran(ParaBlindRun):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = ['safrane', 'syrpluie', 'syrmrr', 'sytist'],
            ),
            date   = a_date,
            members = dict(
                info = "The members that will be processed",
                type = footprints.FPList,
                optional = True
            ),
            terms = dict(
                info = "The list of terms that require an execution.",
                type = footprints.FPList,
            ),
            vconf = dict(
                info    = "The configuration's identifier.",
                alias   = ('configuration',),
                default = '[glove::vconf]',
            ),
        )
    )

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Safran, self)._default_common_instructions(rh, opts)
        ddict['date']  = self.date  # Note: The date could be auto-detected using the sequence
        ddict['vconf'] = self.vconf
        ddict['terms'] = self.terms  # Note: The list of terms could be auto-detected using the sequence
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