#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

"""
AlgoComponents to run Mocage in various modes (forecast, assim, ...).
"""

import six
import io

from bronx.fancies import loggers
from bronx.stdtypes import date

from vortex.algo.components import Parallel, ParallelOpenPalmMixin
from vortex.syntax.stdattrs import a_date, model

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AbstractMocageRoot(Parallel):
    """Abstract Algo component to be used whenever the Mocage model is involved."""

    _abstract = True
    _footprint = [
        model,
        dict(
            info = 'Abstract Mocage AlgoComponent',
            attr = dict(
                kind = dict(
                ),
                basedate = a_date,
                fcterm = dict(
                    info     = 'Forecast term',
                    type     = date.Time,
                ),
                cpldelta = dict(
                    info     = 'Default delta for coupling based on FM files',
                    type     = date.Period,
                    optional = True,
                    default  = 0
                ),
                model = dict(
                    values   = ['mocage', ]
                ),
                flyargs = dict(
                    default  = ('HM', ),
                ),
                flypoll = dict(
                    default  = 'iopoll_mocage',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'abstract_mocage'

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info('Setup %s macro to %s in %s', macro, value, rh.container.actualpath())

    def prepare(self, rh, opts):
        """ Prepare the synchronisation with next tasks"""
        # to control synchronisation and promised files: use the script in iopoll method
        # The script executed via iopoll method returns the list of promised files ready
        if self.promises:
            self.io_poll_kwargs = dict(vconf=rh.provider.vconf.upper())
            self.flyput = True
        else:
            self.flyput = False

        super(AbstractMocageRoot, self).prepare(rh, opts)

    def _sorted_inputs_terms(self, **kwargs):
        """
        Build a dictionary that contains a list of sections for each geometry
        :param kwargs: attributes that will be used to sort the input files
        :return: a dictionary like:
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

    def _prepare_mocage_fc_namelist(self):
        """Look for a forecast namelist + input files and unpdate the namelist."""

        # Forecast namelist
        namrh = self.context.sequence.effective_inputs(
            role='NamelistForecastSettings',
            kind='namelist',)
        if len(namrh) != 1:
            logger.critical('There must be exactly one <input fcst> namelist for forecast execution. Stop.')
            raise ValueError('There must be exactly one namelist for mocage execution. Stop.')

        namrh = namrh[0].rh

        # Build dictionaries which contains the terms for each geometry of FM and SM files
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
        maxfm = maxfm - minfm + int(self.cpldelta.total_seconds() // 3600)

        realfcterm = min(maxsm, maxfm, self.fcterm.hour)
        logger.info('Min Max( fmterms) : %04d %d', minfm, maxfm)
        logger.info('Min Max (smterms) : %04d %d', minsm, maxsm)
        logger.info('self.fcterm.hour  :      %d', self.fcterm.hour)
        logger.info('Fcterm            :      %d', realfcterm)

        first = self.basedate
        last = self.basedate + date.Period(hours=realfcterm)

        if self.fcterm != six.text_type(realfcterm):
            self.system.title('Forecast final term modified : {0:d} '.format(realfcterm))

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

        return date.Period(hours=realfcterm)


class Forecast(AbstractMocageRoot):
    """Algo component for mocage forecasts"""

    _footprint = dict(
        info = 'Mocage forecast',
        attr = dict(
            kind = dict(
                values = ['forecast'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'forecast'

    def execute(self, rh, opts):
        """Standard execution."""
        self._prepare_mocage_fc_namelist()
        super(Forecast, self).execute(rh, opts)


class AssimilationOpenPalm(AbstractMocageRoot, ParallelOpenPalmMixin):
    """Algo component for assimilation in Mocage using PALM.

    Palm Driver + 1 main_block1 on first node
    """

    _footprint = dict(
        info = 'Mocage assimilation using PALM',
        attr = dict(
            kind = dict(
                values      = ['palm_assim', ],
            ),
            cpldelta = dict(
                default     = date.Period(hours=3),
            ),
            assimwindowlen = dict(
                info        = "The duration of an assimilation window",
                type        = date.Period,
                optional    = True,
                default     = date.Period(hours=1),
            ),
            binarysingle = dict(
                default     = 'mocagepalm',  # Will set OpenMP environment variables
            ),
        )
    )

    @property
    def realkind(self):
        return 'assimilation'

    def prepare(self, rh, opts):
        """Export some variables that are specific to MOCAGE-assim."""
        self.export('mocage-assim')
        super(AssimilationOpenPalm, self).prepare(rh, opts)

    def execute(self, rh, opts):
        """Standard execution."""
        realfcterm = self._prepare_mocage_fc_namelist()

        # Process JSON config file for assimilation
        json_inputs = self.context.sequence.effective_inputs(role='AssimilationSettings')
        if len(json_inputs) != 1:
            logger.critical('There must be exactly one json assimilation namelist for mocage/assim execution. Stop.')
            raise ValueError('There must be exactly one json assimilation namelist. Stop.')
        json_rh = json_inputs[0].rh
        json_rh.contents.data['Assimilation']['Cycling']['NbOfWindows'] = int(realfcterm.total_seconds() /
                                                                              self.assimwindowlen.total_seconds())
        json_rh.save()
        json_rh.container.cat()

        super(AssimilationOpenPalm, self).execute(rh, opts)


class Init(Parallel):
    """Algo component for Init."""

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
    """Algo component for TSTRESTART."""

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
