#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

"""
AlgoComponents for MOCAGE post-processing.
"""

import re

from bronx.datagrip.namelist import NamelistBlock
from bronx.fancies import loggers
import footprints

from vortex.algo.components import Parallel, BlindRun, Expresso
from vortex.syntax.stdattrs import model

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class PPCamsBDAP(BlindRun):
    """
    Post-processing of mocage/cams fc for BDAP.
    """

    _footprint = [
        model,
        dict(
            info = 'Post-processing of mocage/cams fc for BDAP',
            attr = dict(
                kind = dict(
                    values   = ['ppcamsbdap'],
                ),
                model = dict(
                    values   = ['mocage']
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'namelistgrib2.nam',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ppcamsbdap'

    def execute(self, rh, opts):
        """Standard execution."""

        sh = self.system

        # Namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for maccraq execution. Stop.')
            raise ValueError('There must be exactly one namelist for maccraq execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()
        refblock = NamelistBlock(name='MACCRAQ_IN')
        refblock.update(namrh.contents['MACCRAQ_IN'])

        # HM files from forecast
        hmrh = self.context.sequence.effective_inputs(
            role='HMFiles',
            kind='gridpoint' )
        # overwrite hmrh by the ascending sort of the hmrh list
        hmrh.sort(key=lambda s: s.rh.resource.term)

        for i in hmrh:
            r = i.rh

            # wait for the next HM netcdf file to be translated in grib2 format
            self.grab(i, comment='forecast outputs moved to grib2 format')

            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                  r.resource.term.fmthm))
            actualdate = r.resource.date + r.resource.term

            # Get a temporary namelist container
            newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')

            # Substitute macros in namelist
            myblock = namrh.contents['MACCRAQ_IN']
            myblock.clear()
            myblock.update(refblock)
            myblock.addmacro('YYYY', actualdate.year)
            myblock.addmacro('MM', actualdate.month)
            myblock.addmacro('DD', actualdate.day)
            myblock.addmacro('HH', actualdate.hour)
            myblock.addmacro('YYYYMMJJBASE', int(r.resource.date.ymd))
            myblock.addmacro('ST', int(r.resource.term.hour))

            namrh.contents.rewrite(newcontainer)
            newcontainer.cat()

            # Link in the forecast file
            self.system.softlink(r.container.localpath(), 'HMFILE.nc')

            # Execute
            super(PPCamsBDAP, self).execute(rh, opts)

            newcontainer.clear()

            actualname = 'MFM_' + actualdate.ymdh + '.grib2'
            if self.system.path.exists('MFM_V5-.grib2'):
                sh.mv('MFM_V5-.grib2', actualname)
            if self.system.path.exists('MFM_V5+.grib2'):
                sh.mv('MFM_V5+.grib2', actualname)

            sh.rmall('HMFILE.nc', 'HM_HYBRID.nc', 'HM.nc')

            # The grib2 output may be promised for BDAP transferts : put method applied to these outputs
            # put these outputs in the cache ; IGA will perform the following actions.
            expected = [x for x in self.promises
                        if (re.match(actualname, x.rh.container.localpath()) ) ]
            for thispromise in expected:
                thispromise.put(incache=True)


class MkStatsCams(Expresso):

    _footprint = dict(
        info = 'Produce some statistics after a mocage forecast',
        attr = dict(
            interpreter = dict(
                optional = True,
                default  = 'python',
                values = ['python', 'current'],
            ),
            engine = dict(
                values = ['mkstcams']
            )
        )
    )

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        hmfiles = self.context.sequence.effective_inputs(
            role='HMBroadcastFiles',
            kind='gridpoint'
        )

        # We take any input file to guess prefix and mask
        example = hmfiles[0].rh

        # Let's assume that prefix and mask are separated by a '+' and split filename
        actualprefix, actualmask = example.container.localpath().split('+', 1)

        # Replacing any leading digit with a wildcard '?'
        x = re.match(r'(\d+)', actualmask)
        if x:
            digits = len(x.group(0))
            actualmask = '?' * digits + actualmask[digits:]

        return dict(
            prefix  = '"' + actualprefix + '+"',
            mask    = '"' + actualmask + '"',
            verbose = '',
        )


class PPprevairBDAP(Parallel):
    """
    Post-processing of mocage/prevair fc for BDAP.
    """

    _footprint = [
        model,
        dict(
            info = 'Post-processing of mocage/prevair fc for BDAP',
            attr = dict(
                kind = dict(
                    values   = ['ppprevairbdap'],
                ),
                model = dict(
                    values   = ['mocage'],
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'PREVIBASE_param.nam',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ppprevairbdap'

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system

        # Namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for hmsplit_grib2 execution. Stop.')
            raise ValueError('There must be exactly one namelist for hmsplit_grib2 execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()

        # save the parametrized namelist
        sh.cp('PREVIBASE.nam', 'PREVIBASE_param.nam')

        # HM files from forecast
        hmrh = self.context.sequence.effective_inputs(
            role='HMFiles',
            kind='GridPoint' )
        logger.info('Number of HMFilesFA %d ', len(hmrh))

        if len(hmrh) == 0:
            logger.critical('There must be HM files to be opened by hmsplit_grib execution. Stop.')
            raise ValueError('There must be HM files to be opened by hmsplit_grib2 execution. Stop.')

        # overwrite hmrh by the ascending sort of the hmrh list
        hmrh.sort(key=lambda s: s.rh.resource.term)

        for i in hmrh:
            r = i.rh

            # wait for the next HM fa file to be translated in grib2 format
            self.grab(i, comment='forecast outputs moved to grib2 format')

            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                  r.resource.term.fmthm))
            actualdate = r.resource.date + r.resource.term

            # Get a new parametrized namelist
            sh.cp('PREVIBASE_param.nam', 'PREVIBASE.nam', intent='in')
            sh.cat('PREVIBASE.nam', output=False)

            self._fix_nam_macro(namrh, 'YYYY', int(r.resource.date.year))
            self._fix_nam_macro(namrh, 'MM', int(r.resource.date.month))
            self._fix_nam_macro(namrh, 'DD', int(r.resource.date.day))
            self._fix_nam_macro(namrh, 'HH', int(r.resource.term))
            self._fix_nam_macro(namrh, 'DATEECH', int(actualdate.ymdh))

            namrh.save()
            namrh.container.cat()

            # Execute
            super(PPprevairBDAP, self).execute(rh, opts)

            actualname = 'GRIB_BDAP_' + actualdate.ymdh
            # The grib2 output may be promised for BDAP transferts : put method
            # applied to these outputs. put these outputs in the cache ; IGA
            # will perform the following actions.
            expected = [x for x in self.promises
                        if (re.match(actualname, x.rh.container.localpath()) ) ]
            for thispromise in expected:
                thispromise.put(incache=True)
