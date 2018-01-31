#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import Parallel, BlindRun
from vortex.syntax.stdattrs import a_date
from bronx.stdtypes import date

class Corromegasurf(Parallel):
    """Corromegasurf"""

    _footprint = dict(
        info='Corromegasurf',
        attr=dict(
            kind=dict(
                values=['corromegasurf'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'corromegasurf'

    def prepare(self, rh, opts):

        # Let ancestors handling most of the env setting
        super(Corromegasurf, self).prepare(rh, opts)

        sh = self.system

        gridrh = self.context.sequence.effective_inputs(
            role=('IfsFiles'),
            kind=('gridpoint')
        )
        gridrh.sort(key=lambda s: s.rh.resource.term)

        sh.remove('fort.2')
        list_file = [filerh.rh.container.filename for filerh in gridrh]
        list_file = "\n".join([str(len(list_file))]+list_file)

        with open('fort.2', 'w') as fnam:
            fnam.write(list_file)
        sh.cat('fort.2')


    def execute(self, rh, opts):
        """Standard execution."""

        super(Corromegasurf, self).execute(rh, opts)



class Surface(Parallel):
    """Algo component for Sumo"""

    _footprint = dict(
        info='Surface',
        attr=dict(
            kind=dict(
                values=['surface'],
            ),
            cfgfile=dict(
                info='Radical of the name of the configuration file',
                type=str,
                optional=True,
                default='RACMOBUS_MACCOPER2016',
            ),
        )
    )

    @property
    def realkind(self):
        return 'surface'

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
        sh.cp(namrh.container.localpath(), 'nam_init')

        # Grib files from Ifs MET*
        gribrh = self.context.sequence.effective_inputs(
            role='GribFilesFromIfs',
            kind='gridpoint', )

        for i in gribrh:
            sh.cp('nam_init',namrh.container.localpath())
            r = i.rh
            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                           r.resource.term.fmthm))
            actualdate = r.resource.date + r.resource.term
            cfgfile = self.cfgfile + '.' + r.resource.geometry.area + '.cfg'

            self._fix_nam_macro(namrh, 'YYYY', int(actualdate.year))
            self._fix_nam_macro(namrh, 'MM', int(actualdate.month))
            self._fix_nam_macro(namrh, 'DD', int(actualdate.day))
            self._fix_nam_macro(namrh, 'DOMAIN', r.resource.geometry.area)
            self._fix_nam_macro(namrh, 'CFGFILE', cfgfile )

            namrh.contents.rewrite(namrh.container)
            namrh.container.cat()

            super(Surface, self).execute(rh, opts)

class Fire(Parallel):
    """Algo component for sumo (fire task) EN COURS DE DEV ne pas utiliser"""

    _footprint = dict(
        info='Fire',
        attr=dict(
            kind=dict(
                values=['fire'],
            ),
            cfgfile=dict(
                info='Radical of the name of the configuration file',
                type=str,
                optional=True,
                default='RACMOBUS_MACCOPER2016_BB',
            ),
            domain=dict(
                info='Domains',
                type=footprints.FPList,
            ),
            basedate=a_date,
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
        sh.cp(namrh.container.localpath(), 'nam_init')

        # Loop on domains

        for domain in self.domain:
            sh.cp('nam_init',namrh.container.localpath())

            sh.title('Loop on domain {0:s}'.format(domain))
            cfgfile = self.cfgfile + '.' + domain + '.cfg'

            self._fix_nam_macro(namrh, 'YYYY', int(self.basedate.year))
            self._fix_nam_macro(namrh, 'MM', int(self.basedate.month))
            self._fix_nam_macro(namrh, 'DD', int(self.basedate.day))
            self._fix_nam_macro(namrh, 'DOMAIN', domain)
            self._fix_nam_macro(namrh, 'CFGFILE', cfgfile )

            namrh.contents.rewrite(namrh.container)
            namrh.container.cat()

            super(Fire, self).execute(rh, opts)


class Mktopbd(BlindRun):
    """Algo component for Mktopbd"""

    _footprint = dict(
        info='Mktopbd algo component',
        attr=dict(
            kind=dict(
                values=['mktopbd'],
            ),
            fcterm=dict(
                info='Forecast term',
                type=int,
            ),
            basedate=a_date,
        )
    )

    @property
    def realkind(self):
        return 'mktopbd'

    def spawn_stdin_options(self):
        """Build the dictionnary to provide arguments to the binary."""
        return dict(
            fcterm=self.fcterm,
            basedate=self.basedate,
        )


class Grib(BlindRun):
    """Algo component for maccraq binary"""

    _footprint = dict(
        info='Cams fullpos',
        attr=dict(
            kind=dict(
                values=['grib'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'grib'

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
            logger.critical('There must be exactly one namelist for maccraq execution. Stop.')
            raise ValueError('There must be exactly one namelist for maccraq execution. Stop.')

        namrh = namrh[0].rh
        sh.cp(namrh.container.localpath(), 'nam_init')

        # Grib files from forecast
        gribrh = self.context.sequence.effective_inputs(
            role='GribFiles',
            kind='gridpoint' )

        for i in gribrh:
            r = i.rh

            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                  r.resource.term.fmthm))
            sh.cp('nam_init',namrh.container.localpath())
            actualdate = r.resource.date + r.resource.term

            self._fix_nam_macro(namrh, 'YYYY', int(actualdate.year))
            self._fix_nam_macro(namrh, 'MM', int(actualdate.month))
            self._fix_nam_macro(namrh, 'DD', int(actualdate.day))
            self._fix_nam_macro(namrh, 'HH', int(actualdate.hour))
            self._fix_nam_macro(namrh, 'YYYYMMJJBASE', int(r.resource.date.ymd))
            self._fix_nam_macro(namrh, 'ST', int(r.resource.term.hour))
            namrh.contents.rewrite(namrh.container)
            namrh.container.cat()

            # Load miscellaneous modules
            lpath = r.container.localpath()
            cmd1 = '. /etc/profile.d/00-modules.sh; set -x ; module load gnu; module load gcc; module load nco; module load cdo; module load netcdf; module load jasper; ncks -O -v a_hybr_coord,b_hybr_coord ' + lpath + ' HM_HYBRID.nc'
            cmd2 = '. /etc/profile.d/00-modules.sh; set -x; module load gnu; module load gcc; module load nco; module load cdo; module load netcdf; module load jasper; cdo remapbil,regridMACC ' + lpath + ' HMMACC.nc'
            sh.spawn(cmd1, shell=True, output=False, fatal=True)
            sh.spawn(cmd2, shell=True, output=False, fatal=True)

            # Link in the forecast file
            self.system.softlink(r.container.localpath(), 'HMFILE')

            # Execute
            super(Grib, self).execute(rh, opts)

            if self.system.path.exists('MFM_V5-.grib2'):
                sh.mv('MFM_V5-.grib2','MFM_' + actualdate.ymdh + '.grib2')
            if self.system.path.exists('MFM_V5+.grib2'):
                    sh.mv('MFM_V5+.grib2', 'MFM_' + actualdate.ymdh + '.grib2')

            sh.rmall('HMFILE', 'HM_HYBRID.nc','HM.nc')

class Forecast(Parallel):
    """Algo component for mocage binary"""

    _footprint = dict(
        info='Mocage forecast',
        attr=dict(
            kind=dict(
                values=['forecast'],
            ),
            basedate=a_date,
            fcterm=dict(
                info='Forecast term',
                type=int,
                optional=True,
            ),
        )
    )

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
            role='Namelist(inputFcst)',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one <input fcst> namelist for forecast execution. Stop.')
            raise ValueError('There must be exactly one namelist for sumo execution. Stop.')

        namrh = namrh[0].rh

        first = self.basedate
        lterm = 'PT' + str(self.fcterm) + 'H'
        last= self.basedate + date.Period(lterm)

        self._fix_nam_macro(namrh, 'YYYY1', int(first.year))
        self._fix_nam_macro(namrh, 'YYYY2', int(last.year))
        self._fix_nam_macro(namrh, 'MM1', int(first.month))
        self._fix_nam_macro(namrh, 'MM2', int(last.month))
        self._fix_nam_macro(namrh, 'DD1', int(first.day))
        self._fix_nam_macro(namrh, 'DD2', int(last.day))
        self._fix_nam_macro(namrh, 'HH1', int(first.hour))
        self._fix_nam_macro(namrh, 'HH2', int(last.hour))

        namrh.contents.rewrite(namrh.container)
        namrh.container.cat()

        super(Forecast, self).execute(rh, opts)

