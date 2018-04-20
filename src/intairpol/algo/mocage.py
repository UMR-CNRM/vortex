#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

import io
import re
import six

import footprints

from vortex.algo.components import Parallel, BlindRun, Expresso
from vortex.syntax.stdattrs import a_date, model
from bronx.stdtypes import date
from bronx.datagrip.namelist import NamelistBlock

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class CorrOmegaSurf(Parallel):
    """Correction of vertical velocity at surface level."""

    _footprint = [
        model,
        dict(
            info = 'Correction of vertical velocity at surface level',
            attr = dict(
                kind = dict(
                    values = ['corromegasurf'],
                ),
                model = dict(
                    values = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'corromegasurf'

    def prepare(self, rh, opts):

        # Let ancestors handling most of the env setting
        super(CorrOmegaSurf, self).prepare(rh, opts)

        sh = self.system

        gridrh = self.context.sequence.effective_inputs(
            role=('AltitudeFields'),
            kind=('gridpoint')
        )
        gridrh.sort(key=lambda s: s.rh.resource.term)

        sh.remove('fort.2')
        list_file = [six.text_type(filerh.rh.container.localpath()) for filerh in gridrh]
        list_file = "\n".join([six.text_type(len(list_file)), ] + list_file)

        with io.open('fort.2', 'w') as fnam:
            fnam.write(list_file)
        sh.cat('fort.2')


class Surface(Parallel):
    """Algo component for Sumo"""

    _footprint = [
        model,
        dict(
            info = 'Surface',
            attr = dict(
                kind = dict(
                    values   = ['surface'],
                ),
                cfgfile = dict(
                    info     = 'Radical of the name of the configuration file',
                    optional = True,
                    default  = 'RACMOBUS_MACCOPER2016',
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'SUMO_IN',
                ),
                model = dict(
                    values   = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'surface'

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system

        # Sumo namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for sumo execution. Stop.')
            raise ValueError('There must be exactly one namelist for sumo execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()
        refblock = NamelistBlock(name=self.namelist_name)
        refblock.update(namrh.contents[self.namelist_name])

        # Grib files from IFS MET*
        gribrh = self.context.sequence.effective_inputs(
            role='SurfaceFields',
            kind='gridpoint')

        for i in gribrh:
            r = i.rh
            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                  r.resource.term.fmthm))
            actualdate = r.resource.date + r.resource.term

            # Get a temporary namelist container
            newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')

            # Substitute macros in namelist
            myblock = namrh.contents[self.namelist_name]
            myblock.clear()
            myblock.update(refblock)
            myblock.addmacro('YYYY', actualdate.year)
            myblock.addmacro('MM', actualdate.month)
            myblock.addmacro('DD', actualdate.day)
            myblock.addmacro('DOMAIN', r.resource.geometry.area)
            myblock.addmacro('CFGFILE', self.cfgfile + '.' + r.resource.geometry.area + '.cfg')

            namrh.contents.rewrite(newcontainer)
            newcontainer.cat()

            super(Surface, self).execute(rh, opts)

            newcontainer.clear()


class Fire(Parallel):
    """Algo component for sumo (fire task)"""

    _footprint = dict(
        info = 'Fire',
        attr = dict(
            kind = dict(
                values = ['fire'],
            ),
            cfgfile = dict(
                info     = 'Radical of the name of the configuration file',
                optional = True,
                default  = 'RACMOBUS_MACCOPER2016_BB',
            ),
            namelist_name = dict(
                info     = 'Namelist name for the binary',
                optional = True,
                default  = 'SUMO_IN',
            ),
        )
    )

    @property
    def realkind(self):
        return 'fire'

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def execute(self, rh, opts):
        """Standard execution."""

        sh = self.system

        # Sumo namelist
        namrh = self.context.sequence.effective_inputs(
            role='Namelist',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one namelist for sumo execution. Stop.')
            raise ValueError('There must be exactly one namelist for sumo execution. Stop.')

        namrh = namrh[0].rh
        if not namrh.container.is_virtual() and sh.path.basename(namrh.container.localpath()) == self.namelist_name:
            logger.critical('The namelist cannot be named "%s".', self.namelist_name)
            raise ValueError()
        refblock = NamelistBlock(name=self.namelist_name)
        refblock.update(namrh.contents[self.namelist_name])

        # Loop on domains
        obsrh = self.context.sequence.effective_inputs(
            role='ObservationsFire',
            kind='obsfire')

        for r_obs in obsrh:
            r = r_obs.rh

            sh.title('Loop on domain {0:s}'.format(r.resource.geometry.area))

            # Create symlinks for fire obsfiles
            obsfiles = sh.ls(r.container.localpath())
            for i in obsfiles:
                path = r.container.localpath() + '/' + i
                sh.symlink(path, i)

            # Get a temporary namelist container
            newcontainer = footprints.proxy.container(filename=self.namelist_name, format='txt')

            # Substitute macros in namelist
            myblock = namrh.contents[self.namelist_name]
            myblock.clear()
            myblock.update(refblock)
            myblock.addmacro('YYYY', r.resource.date.year)
            myblock.addmacro('MM', r.resource.date.month)
            myblock.addmacro('DD', r.resource.date.day)
            myblock.addmacro('DOMAIN', r.resource.geometry.area)
            myblock.addmacro('CFGFILE', self.cfgfile + '.' + r.resource.geometry.area + '.cfg')

            namrh.contents.rewrite(newcontainer)
            newcontainer.cat()

            super(Fire, self).execute(rh, opts)

            newcontainer.clear()

            # Remove symlinks
            for i in obsfiles:
                sh.remove(i)


class Mktopbd(BlindRun):
    """Algo component for Mktopbd"""

    _footprint = [
        model,
        dict(
            info = 'Mktopbd algo component',
            attr = dict(
                kind = dict(
                    values = ['mktopbd'],
                ),
                basedate = a_date,
                fcterm = dict(
                    info = 'Forecast term',
                    type = date.Time,
                ),
                model = dict(
                    values = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'mktopbd'

    def spawn_stdin_options(self):
        """Build the dictionnary to provide arguments to the binary."""
        return dict(
            fcterm   = self.fcterm,
            basedate = self.basedate,
        )


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

        for i in hmrh:
            r = i.rh

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

            # Load miscellaneous modules
            # FIXME: At least before it becomes operational !
            lpath = r.container.localpath()
            cmd1 = '. /etc/profile.d/00-modules.sh; module load gcc; module load nco; module load cdo; module load netcdf; module load jasper; module list; ncks -O -v a_hybr_coord,b_hybr_coord ' + lpath + ' HM_HYBRID.nc'
            cmd2 = '. /etc/profile.d/00-modules.sh; module load gcc; module load nco; module load cdo; module load netcdf; module load jasper; module list; cdo remapbil,regridMACC ' + lpath + ' HMMACC.nc'
            sh.spawn(cmd1, shell=True, output=False, fatal=True)
            sh.spawn(cmd2, shell=True, output=False, fatal=True)

            # Link in the forecast file
            self.system.softlink(r.container.localpath(), 'HMFILE')

            # Execute
            super(PPCamsBDAP, self).execute(rh, opts)

            newcontainer.clear()

            if self.system.path.exists('MFM_V5-.grib2'):
                sh.mv('MFM_V5-.grib2', 'MFM_' + actualdate.ymdh + '.grib2')
            if self.system.path.exists('MFM_V5+.grib2'):
                sh.mv('MFM_V5+.grib2', 'MFM_' + actualdate.ymdh + '.grib2')

            sh.rmall('HMFILE', 'HM_HYBRID.nc', 'HM.nc')


class Forecast(Parallel):
    """Algo component for mocage binary"""

    _footprint = [
        model,
        dict(
            info = 'Mocage forecast',
            attr = dict(
                kind = dict(
                    values = ['forecast'],
                ),
                basedate = a_date,
                fcterm = dict(
                    info   = 'Forecast term',
                    type   = date.Time,
                ),
                model = dict(
                    values = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'forecast'

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def execute(self, rh, opts):
        """Standard execution."""

        # Forecast namelist
        namrh = self.context.sequence.effective_inputs(
            role='NamelistForecastSettings',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one <input fcst> namelist for forecast execution. Stop.')
            raise ValueError('There must be exactly one namelist for mocage execution. Stop.')

        namrh = namrh[0].rh

        first = self.basedate
        last = self.basedate + self.fcterm

        self._fix_nam_macro(namrh, 'YYYY1', int(first.year))
        self._fix_nam_macro(namrh, 'YYYY2', int(last.year))
        self._fix_nam_macro(namrh, 'MM1', int(first.month))
        self._fix_nam_macro(namrh, 'MM2', int(last.month))
        self._fix_nam_macro(namrh, 'DD1', int(first.day))
        self._fix_nam_macro(namrh, 'DD2', int(last.day))
        self._fix_nam_macro(namrh, 'HH1', int(first.hour))
        self._fix_nam_macro(namrh, 'HH2', int(last.hour))

        namrh.save()
        namrh.container.cat()

        super(Forecast, self).execute(rh, opts)


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
            role=('HMBroadcastFiles'),
            kind=('gridpoint')
        )

        # We take any input file to guess prefix and mask
        example = hmfiles[0].rh

        # Let's assume that prefix and mask are separated by a '+' and split filename
        actualprefix, actualmask = example.container.localpath().split('+', 1)

        # Replacing any leading digit with a wildcard '?'
        x = re.match('(\d+)', actualmask)
        if x:
            digits = len(x.group(0))
            actualmask = '?' * digits + actualmask[digits:]

        return dict(
            prefix  = '"' + actualprefix + '+"',
            mask    = '"' + actualmask + '"',
            verbose = '',
        )
