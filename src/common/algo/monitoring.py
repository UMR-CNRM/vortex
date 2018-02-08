#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: Automatic export of Monitoring class
__all__ = [ ]

import footprints

logger = footprints.loggers.getLogger(__name__)

from vortex.syntax.stdattrs import a_date, a_model, a_cutoff
from common.algo.odbtools import OdbProcess


class OdbMonitoring(OdbProcess):
    """Compute monitoring statistics"""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['monitoring'],
            ),
            npool = dict(
                default = 1,
                optional = True,
            ),
            obs = dict(
                values = ['all', 'used'],
            ),
            date = a_date,
            model= a_model,
            cutoff = a_cutoff,
            start = dict(
                type  = bool,
                default = False,
                optional = True,
            ),
            cumul = dict(
                type = bool,
                default = True,
                optional = True,
            ),
            extend = dict(
                type = bool,
                default = False,
                optional = True,
            ),
            stage = dict(
                values = ['can', 'surf', 'surface', 'atm', 'atmospheric'],
                remap = dict(can='surf', surface='surf', atmospheric='atm'),
                info = 'The processing stage of the ODB base.',
            ),
        )
    )

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def prepare(self, rh, opts):
        """Update some variables in the namelist and verify the presence or not of the accumulated statistics file"""

        # Let ancestors handling most of the env setting
        super(OdbMonitoring, self).prepare(rh, opts)

        sh = self.system

        # Looking for input observations
        obsmatchup = [
            x for x in self.input_obs()
            if x.resource.stage.startswith('matchup') and x.resource.part == 'virtual'
        ]

        obssurf = [
            x for x in self.input_obs()
            if x.resource.stage.startswith('canari') and (x.resource.part == 'surf' or x.resource.part == 'ground')
        ]

        # One database at a time
        if not obsmatchup and self.stage == 'atm':
            raise ValueError('Could not find any ODB matchup input')
        if not obssurf and self.stage == 'surf':
            raise ValueError('Could not find any ODB surface input')

        # Set actual ODB paths
        if obsmatchup:
            ecma = obsmatchup.pop(0)
        else:
            ecma = obssurf.pop(0)
        ecma_path = sh.path.abspath(ecma.container.localpath())
        self.env.ODB_SRCPATH_ECMA = ecma_path
        logger.info('Setting ODB env %s = %s.', 'ODB_SRCPATH_ECMA', ecma_path)
        self.env.ODB_DATAPATH_ECMA = ecma_path
        logger.info('Setting ODB env %s = %s.', 'ODB_DATAPATH_ECMA', ecma_path)
        self.env.IOASSIGN = sh.path.join(ecma_path, 'IOASSIGN')
        logger.info('Setting ODB env %s = %s.', 'IOASSIGN', sh.path.join(ecma_path, 'IOASSIGN'))

        # Force to start a new accumulated statistics file if first day and first hour of the month
        mnt_start = self.start

        if not mnt_start and int(self.date.day) == 1 and int(self.date.hh) == 0 and not self.extend:
            logger.info('First day and first hour of the month : force start attribute to True.')
            mnt_start = True

        mnt_cumul = self.cumul
        if self.cutoff == 'production':
            mnt_cumul = False
            logger.info('No output accumulated statistics file will be produced because cutoff = production : force cumul to False')

        # Monitoring namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for monitoring. Stop.')
            raise ValueError('There must be exactly one namelist for monitoring. Stop.')
        namrh = namrh[0].rh

        # Cumulated statistics file
        cumulrh = self.context.sequence.effective_inputs(
            role='Cumulated monitoring statistics',
            kind='accumulated_stats',
        )

        if len(cumulrh) > 1:
            logger.critical('There must be at most one accumulated statistics file.Stop.')
            raise ValueError('There must be one accumulated statistics file or none.Stop.')
        else:
            if len(cumulrh) == 0:
                if not mnt_start:
                    if mnt_cumul:
                        logger.critical('There must be one input accumulated statistics file. Stop.')
                        raise ValueError('There must be one input accumulated statistics file. Stop.')
                    else:
                        logger.info('No input accumulated statistics file is necessary.')
                        logger.info('No output accumulated statistics file will be produced.')
                else:
                    if mnt_cumul:
                        logger.info('No input accumulated statistics file. It will be created by the binary.')
                    else:
                        logger.info('No output accumulated statistics file will be produced.')
            else:
                cumulrh = cumulrh[0].rh
                if not mnt_cumul:
                    logger.info('No input accumulated statistics file is necessary(start=False).')
                    cumulrh.container.clear()
                else:
                    if mnt_start:
                        logger.info('No input accumulated statistics file is necessary (start=True)')
                        cumulrh.container.clear()

        self._fix_nam_macro(namrh, 'JOUR', int(self.date.ymd))
        self._fix_nam_macro(namrh, 'RES', int(self.date.hh))

        self._fix_nam_macro(namrh, 'LLADMON', mnt_cumul)
        self._fix_nam_macro(namrh, 'LLADAJ', mnt_cumul and not mnt_start)

        self._fix_nam_macro(namrh, 'LLFLAG', self.obs != 'all')

        self._fix_nam_macro(namrh, 'LLARO', self.model == 'arome')
        self._fix_nam_macro(namrh, 'LLVRP', self.model == 'varpack')
        self._fix_nam_macro(namrh, 'LLCAN', self.stage == 'surf')

        namrh.contents.rewrite(namrh.container)
        namrh.container.cat()

    def postfix(self, rh, opts):
        """Remove all empty files and find out if any special resources have been produced."""

        sh = self.system
        self.system.dir(output = False, fatal=False)
        allfiles = sh.ls()
        for f in allfiles:
            if self.system.path.getsize(f) == 0:
                logger.info('Remove %s because size of %s is zero.', f, f)
                sh.remove(f)

        obspoint_out = sh.ls('point.*')
        if obspoint_out:
            dest = 'obslocationpack'
            logger.info('Creating an OBSLOCATION pack: %s', dest)
            sh.mkdir(dest)
            for fname in obspoint_out:
                sh.mv(fname, dest)
        self.system.dir(output=False, fatal=False)
