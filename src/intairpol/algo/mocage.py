#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

import six
import io
import re

from bronx.datagrip.namelist import NamelistBlock
from bronx.fancies import loggers
from bronx.stdtypes import date
import footprints

from vortex.algo.components import Parallel, BlindRun, Expresso
from vortex.syntax.stdattrs import a_date, model

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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
            role='AltitudeFields',
            kind='gridpoint'
        )
        gridrh.sort(key=lambda s: s.rh.resource.term)

        sh.remove('fort.2')
        list_file = [six.text_type(filerh.rh.container.localpath()) for filerh in gridrh]
        list_file = "\n".join([six.text_type(len(list_file)), ] + list_file)

        with io.open('fort.2', 'w') as fnam:
            fnam.write(list_file)
        sh.cat('fort.2', output=False)


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
        # Sm files
        smrh = self.context.sequence.effective_inputs(
            role='SMFiles',
            kind='boundary')

        if smrh:
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
        else:
            logger.warning('No SM files')


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
                ),
                flyargs = dict(
                    default = ('HM', ),
                ),
                flypoll = dict(
                    default = 'iopoll_mocage',
                ),
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

    def prepare(self, rh, opts):
        """ Prepare the synchronisation with next tasks"""
        # to control synchronisation and promised files : use the script in iopoll method
        # The script executed via iopoll method returns the list of promised files ready
        if self.promises:
            self.io_poll_kwargs = dict(vconf=rh.provider.vconf.upper())
            self.flyput = True
        else:
            self.flyput = False

        super(Forecast, self).prepare(rh, opts)

    def _sorted_inputs_terms(self, **kwargs):
        """
        Build a dictionnary that contains a list of sections for each geometry
        :param kwargs: attributes that will be used to sort the input files
        :return: a dictionnary like:
        {'geometry1': [terms1, terms2, ...],
         'geometry2': [terms1, terms2, ...]
        }
        """
        # Find the input files
        insec = self.context.sequence.effective_inputs(**kwargs)
        # Initialize the output dictionnary
        outdict = dict()
        # Fill the dictionnary
        for sec in insec:
            geo = sec.rh.resource.geometry.area
            if geo not in outdict:
                outdict[geo] = list()
            outdict[geo].append(int(sec.rh.resource.term.fmth))
        for geo in outdict:
            outdict[geo].sort()
        return outdict

    def execute(self, rh, opts):
        """Standard execution."""

        sh = self.system

        # First : Prepare namelist substitutions

        # Forecast namelist
        namrh = self.context.sequence.effective_inputs(
            role='NamelistForecastSettings',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one <input fcst> namelist for forecast execution. Stop.')
            raise ValueError('There must be exactly one namelist for mocage execution. Stop.')

        namrh = namrh[0].rh

        # Build dictionnaries which contains the terms for each geometry of FM and SM files
        smterms = self._sorted_inputs_terms(
            role='SMCoupling',
            kind='boundary'
        )
        fmterms = self._sorted_inputs_terms(
            role='FMFiles',
            kind='gridpoint'
        )

        # Control of the duration of the run depending on the the SM and FM terms available
        # Min values indicates whether the resources are nominal or alternate resources
        minsm = max([min(smterms[geo]) for geo in smterms.keys()])
        maxsm = min([max(smterms[geo]) for geo in smterms.keys()])
        # 1 SM file per day and per domain : term 0 is used for the coupling of a 24h run
        maxsm = maxsm - minsm + 24

        minfm = max([min(fmterms[geo]) for geo in fmterms.keys()])
        maxfm = min([max(fmterms[geo]) for geo in fmterms.keys()])
        maxfm = maxfm - minfm

        realfcterm = min(maxsm, maxfm)
        logger.info('Min Max(fmterms) : %s %s ', minfm, maxfm)
        logger.info('Min Max(smterms) : %s %s ', minsm, maxsm)
        logger.info('Fcterm           : %s ', realfcterm)

        first = self.basedate
        deltastr = 'PT' + six.text_type(realfcterm) + 'H'
        last = self.basedate + deltastr

        if self.fcterm != six.text_type(realfcterm):
            sh.title('Forecast final term modified : {0:d} '.format(realfcterm))

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
            role='HMBroadcastFiles',
            kind='gridpoint'
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


class Init(Parallel):
    """Algo component for Init"""

    _footprint = [
        model,
        dict(
            info = 'ClimInit',
            attr = dict(
                kind = dict(
                    values   = ['init'],
                ),
                basedate = a_date,
                model = dict(
                    values   = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'init'

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system

        # execution if relance_clim contains something else than 0
        sh.title('Climatological Init ?  0=No else=yes ')

        restartrh = self.context.sequence.effective_inputs(
            role='ClimRestartFlag',
            kind='restart_flag')

        returncode = True

        if restartrh:
            restartrh = restartrh[0].rh
            restartrh.container.cat()
            returncode = restartrh.contents.restart

        # Run the following lines only if returncode value is not 0
        if returncode:

            namrh = self.context.sequence.effective_inputs(role='Namelist',
                                                           kind='namelist')
            if len(namrh) != 1:
                logger.critical('There must be exactly one namelist for init execution. Stop.')
                raise ValueError('There must be exactly one namelist for init execution. Stop.')

            # Retrieve the domains
            climrh = self.context.sequence.effective_inputs(role='RestartChemicalClimatology',
                                                            kind='clim_misc')
            domains = []
            ldom = []

            for i in climrh:
                r = i.rh
                domains.append(r.resource.geometry.area)
            for i in set(domains):
                ldom.append(i)

            # Substitute date and domains in the namelist
            namrh = namrh[0].rh

            self._fix_nam_macro(namrh, 'YYYY1', int(self.basedate.year))
            self._fix_nam_macro(namrh, 'MM1', int(self.basedate.month))
            self._fix_nam_macro(namrh, 'DD1', int(self.basedate.day))
            self._fix_nam_macro(namrh, 'NBDOM', len(ldom))
            self._fix_nam_macro(namrh, 'DOMAIN', ldom)

            namrh.save()
            namrh.container.cat()

            # Execute the binary
            super(Init, self).execute(rh, opts)
        else:
            # Remove the input HM* files
            for a_file in sh.glob('HM' + '*'):
                sh.remove(a_file)


class ControlGuess(Parallel):
    """Algo component for TSTRESTART"""

    _footprint = [
        model,
        dict(
            info = 'Tstrestart algo component',
            attr = dict(
                kind = dict(
                    values = ['controlguess'],
                ),
                namelist_name = dict(
                    info     = 'Namelist name for the binary',
                    optional = True,
                    default  = 'macc_seuils.nam',
                ),
                model = dict(
                    values = ['mocage']
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'tstrestart'

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system
        sh.title('Dans tstrestar')

        # Fa HM files
        farh = self.context.sequence.effective_inputs(
            role='HMInitialCondition',
            kind='gridpoint')

        # loop on HM files
        total = 0
        for i in farh:
            # Delete the link for the expected input name
            sh.rm('HMFILE')
            r = i.rh
            sh.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                  r.resource.term.fmthm))
            # link to expected input filename
            sh.symlink(r.container.localpath(), 'HMFILE')

            super(ControlGuess, self).execute(rh, opts)

            # get the value written in output file
            sh.title('Climatological Init :  0=No else=yes ')
            sh.pwd()
            sh.ls()
            sh.cat('relance_clim', output=False)

            # get the first line of relance_clim file
            try:
                with io.open('relance_clim', 'r') as fnam:
                    lines = fnam.readlines()
                returncode = lines[0]
                # total stores the returncode values for each domain
                total = total + int(returncode)
            except IOError:
                logger.error('Could not open file relance_clim in read mode')
                raise

        # end of the loop on HM files :
        # write the total value into relance_clim which is read by clim-start
        # if only one guess file is wrong, all domains will be chemical climatologic ones
        logger.info('total %d', total)
        try:
            with io.open('relance_clim', 'w') as fwnam:
                fwnam.write(six.text_type(total))
            sh.title('End of tstrestart : Climatological Inits :  0=No else=yes ')
            sh.cat('relance_clim', output=False)
        except IOError:
            logger.error('Could not open file relance_clim in write mode')
            raise

        sh.cat('relance_clim', output=False)
