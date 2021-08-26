# -*- coding: utf-8 -*-

"""
This modules defines specific CEN addons for the Task base class.
Multiple inheritence together with the standard Task class is required to use this module.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.stdtypes.date import yesterday, Date, Period, Time
from bronx.fancies import loggers
from vortex.tools.actions import actiond as ad
from vortex.algo.components import DelayedAlgoComponentError

logger = loggers.getLogger(__name__)


class S2MTaskMixIn(object):
    """Usefull addtions for any S2M task."""

    nightruntime = Time(hour=3, minute=0)
    firstassimruntime = Time(hour=6, minute=0)
    secondassimruntime = Time(hour=9, minute=0)
    monthly_analysis_time = Time(hour=12, minute=0)

    ref_reanalysis = "reanalysis2020.2@lafaysse"  # Current version of S2M reanalysis

    def s2moper_filter_execution_error(self, exc):
        """Define the behaviour in case of errors.

        For S2M chain, the errors do not raise exception if the deterministic
        run and if less than 5 members produce errors.
        Note than unavailability of members do not produce errors managed by effective_inputs), therefore more than
        5 errors is a critical anomaly.
        """

        warning = {}
        accept_errors = False

        if isinstance(exc, DelayedAlgoComponentError):
            nerrors = len(list(enumerate(exc)))
            warning["nfail"] = nerrors
            determinitic_error = False

            for e in exc:
                if hasattr(e, 'deterministic'):
                    if e.deterministic:
                        determinitic_error = True

                    warning["deterministic"] = e.deterministic

            accept_errors = not determinitic_error and nerrors < 5

        return accept_errors, warning

    def s2moper_report_execution_warning(self, exc, **kw_infos):
        if 'nfail' in kw_infos.keys():
            warning = self.warningmessage(kw_infos['nfail'], exc)
            logger.warning(warning)

            # Add e-mail
            ad.cenmail(to=self.conf.mail_to, id='s2mdev_warning', report=warning)
            # ad.mail(
            #     subject='S2M warning',
            #     to='matthieu.lafaysse@meteo.fr',
            #     contents=warning,
            # )

    def s2moper_report_execution_error(self, exc, **kw_infos):
        if 'nfail' in kw_infos.keys():
            warning = self.warningmessage(kw_infos['nfail'], exc)
            logger.warning(warning)

            # Add e-mail
            ad.cenmail(to=self.conf.mail_to, id='s2mdev_error', report=warning)
            # ad.mail(
            #     subject='S2M fatal error',
            #     to='matthieu.lafaysse@meteo.fr',
            #     contents=warning,
            # )

    def reforecast_filter_execution_error(self, exc):
        warning = {}
        nerrors = len(list(enumerate(exc)))
        warning["nfail"] = nerrors
        accept_errors = nerrors < 5
        if accept_errors:
            print(self.warningmessage(nerrors, exc))
        return accept_errors, warning

    def warningmessage(self, nerrors, exc):
        warningline = "\n" + "!" * 40 + "\n"
        warningmessage = (warningline + "ALERT :" + str(nerrors) +
                          " members produced a delayed exception." +
                          warningline + str(exc) + warningline)
        return warningmessage

    def get_period(self):

        if self.conf.rundate.hour == self.monthly_analysis_time.hour:
            dateendanalysis = self.conf.rundate.replace(hour=6) - Period(days=4)
        elif self.conf.rundate.hour == self.nightruntime.hour:
            dateendanalysis = yesterday(self.conf.rundate.replace(hour=6))
        else:
            dateendanalysis = self.conf.rundate.replace(hour=6)

        if self.conf.previ:
            datebegin = dateendanalysis
            if self.conf.rundate.hour == self.nightruntime.hour:
                dateend = dateendanalysis + Period(days=5)
            else:
                dateend = dateendanalysis + Period(days=4)
        else:
            dateend = dateendanalysis
            if self.conf.rundate.hour == self.nightruntime.hour:
                # The night run performs a 4 day analysis
                datebegin = dateend - Period(days=4)
            elif self.conf.rundate.hour == self.monthly_analysis_time.hour:
                if self.conf.rundate.month <= 7:
                    year = self.conf.rundate.year - 1
                else:
                    year = self.conf.rundate.year
                datebegin = Date(year, 8, 1, 6)
            else:
                # The daytime runs perform a 1 day analysis
                datebegin = dateend - Period(days=1)

        return datebegin, dateend

    def get_rundate_forcing(self):
        if self.conf.previ:
            # SAFRAN only generates new forecasts once a day during the night run
            rundate_forcing = self.conf.rundate.replace(hour=self.nightruntime.hour)
        else:
            # SAFRAN generates new analyses at each run
            rundate_forcing = self.conf.rundate
        return rundate_forcing

    def get_rundate_prep(self):

        alternates = []
        if hasattr(self.conf, 'reinit'):
            reinit = self.conf.reinit
        else:
            reinit = False

        if reinit:
            rundate_prep = self.conf.rundate.replace(hour=self.monthly_analysis_time.hour) - Period(days=1)
            alternates.append((rundate_prep - Period(days=1), "assimilation"))
            alternates.append((rundate_prep - Period(days=2), "assimilation"))
            alternates.append((rundate_prep - Period(days=3), "assimilation"))

        elif self.conf.previ:
            # Standard case: use the analysis of the same runtime
            rundate_prep = self.conf.rundate
            if self.conf.rundate.hour > self.firstassimruntime.hour:
                # First alternate for 09h run: 06h run
                alternates.append((self.conf.rundate.replace(hour=self.firstassimruntime.hour), "assimilation"))
            if self.conf.rundate.hour > self.nightruntime.hour:
                # First alternate for 06h run, second alternate for 09h run: 03h run
                alternates.append((self.conf.rundate.replace(hour=self.nightruntime.hour), "assimilation"))
            # Very last alternates (and only one for 03h run: forecast J+4 of day J-4
            alternates.append((self.conf.rundate.replace(hour=self.secondassimruntime.hour) -
                               Period(days=4), "production"))
            alternates.append((self.conf.rundate.replace(hour=self.firstassimruntime.hour) -
                               Period(days=4), "production"))
            alternates.append((self.conf.rundate.replace(hour=self.nightruntime.hour) -
                               Period(days=4), "production"))

        else:
            if self.conf.rundate.hour == self.monthly_analysis_time.hour:
                if self.conf.rundate.month <= 7:
                    year = self.conf.rundate.year - 1
                else:
                    year = self.conf.rundate.year
                rundate_prep = Date(year, 8, 4, 3)
                alternates.append((rundate_prep - Period(days=1), "assimilation"))
                alternates.append((rundate_prep - Period(days=2), "assimilation"))
                alternates.append((rundate_prep - Period(days=3), "assimilation"))

            # Standard case: use today 03h for 06 et 09h runs, use yesterday 03h for 03h run
            elif self.conf.rundate.hour == self.nightruntime.hour:
                rundate_prep = self.conf.rundate - Period(days=1)
                # First alternate : J-2 for night run, J-1 for other runs
                # Second alternate : J-3 for night run, J-2 for other runs
                # Third alternate : J-4 for night run, J-3 for other runs
                alternates.append((rundate_prep - Period(days=1), "assimilation"))
                alternates.append((rundate_prep - Period(days=2), "assimilation"))
                alternates.append((rundate_prep - Period(days=3), "assimilation"))
                # Desperate case
                alternates.append((rundate_prep - Period(days=8), "production"))

            else:
                rundate_prep = self.conf.rundate.replace(hour=self.nightruntime.hour)
                alternates.append((self.conf.rundate.replace(hour=self.secondassimruntime.hour) -
                                   Period(days=1), "assimilation"))
                alternates.append((self.conf.rundate.replace(hour=self.firstassimruntime.hour) -
                                   Period(days=1), "assimilation"))

        return rundate_prep, alternates

    def get_list_members(self, sytron=True):
        if not self.conf.nmembers:
            raise ValueError
        startmember = int(self.conf.startmember) if hasattr(self.conf, "startmember") else 0
        lastmember = int(self.conf.nmembers) + startmember - 1

        if self.conf.geometry.area == "postes":
            # no sytron members for postes geometry
            return list(range(startmember, lastmember + 1)), list(range(startmember, lastmember + 2))
        elif not sytron:
            return list(range(startmember, lastmember + 1)), list(range(startmember, lastmember + 2))
        else:
            return list(range(startmember, lastmember + 1)), list(range(startmember, lastmember + 3))

    def split_geo_interpol(self):
        geoin, geoout = self.conf.geometry.list.split(":")
        return geoin, geoout

    def get_list_geometry(self, meteo="safran"):

        if hasattr(self.conf, "geoin"):
            return [self.conf.geoin]
        else:
            source_safran, block_safran = self.get_source_safran(meteo=meteo)

            list_suffix = ['_allslopes', '_flat']
            if source_safran == "safran":
                if self.conf.geometry.area == "postes":
                    return self.conf.geometry.list.split(",")
                else:
                    for suffix in list_suffix:
                        if suffix in self.conf.geometry.area:
                            return [self.conf.geometry.area.replace(suffix, '')]
                    return [self.conf.geometry.area]  # for cases with meteo=safran but unknown area
            else:
                return [self.conf.geometry.area]

    def get_alternate_safran(self):
        if self.conf.geometry.area == 'postes':
            return "safran", "postes", self.conf.geometry.list.split(",")
        else:
            return "safran", "massifs", [self.conf.geometry.area[0:3]]

    def get_block_safran_from_geometry(self):
        if self.conf.geometry.area == 'postes':
            return 'postes'
        else:
            return 'massifs'

    def get_source_safran(self, meteo="safran"):

        if hasattr(self.conf, 'blockin'):
            if meteo == "safran":
                return meteo, self.conf.blockin + '/' + self.get_block_safran_from_geometry()
            else:
                return meteo, self.conf.blockin

        elif meteo == "safran":
            if not hasattr(self.conf, "previ"):
                self.conf.previ = False

            if not hasattr(self.conf, 'rundate'):
                return meteo, self.get_block_safran_from_geometry()

            if self.conf.rundate.hour != self.nightruntime.hour and self.conf.previ:
                return "s2m", "meteo"
            else:
                return "safran", self.get_block_safran_from_geometry()
        else:
            return meteo, "meteo"

    def get_safran_sources(self, list_datebegin):

        source_app = dict(
            datebegin={str(datebegin):
                       'arpege' if datebegin >= Date(2002, 8, 1) else 'ifs' for datebegin in list_datebegin})

        source_conf = dict(
            datebegin={str(datebegin):
                       '4dvarfr' if datebegin >= Date(2002, 8, 1) else 'era40' for datebegin in list_datebegin})

        return source_app, source_conf

    def get_list_seasons(self, datebegin, dateend):

        list_dates_begin_input = list()

        if datebegin.month >= 8:
            datebegin_input = Date(datebegin.year, 8, 1, 6, 0, 0)
        else:
            datebegin_input = Date(datebegin.year - 1, 8, 1, 6, 0, 0)
        dateend_input = datebegin_input
        while dateend_input < dateend:
            dateend_input = datebegin_input.replace(year=datebegin_input.year + 1)
            list_dates_begin_input.append(datebegin_input)
            datebegin_input = dateend_input

        return list_dates_begin_input

    def extract_massif(self, massif_to_extract, rawfile, filetype='pro'):

        from snowtools.utils.prosimu import prosimu
        import numpy as np
        from netCDF4 import Dataset
        
        f = prosimu(rawfile)
        time, units = f.readtime_for_copy()
        massifs = f.read_var('massif_num') if filetype == 'pro' else f.read_var('massif_number')
        mask = np.where(massifs == massif_to_extract)

        # Création du fichier de sortie contenant uniquement le massif désiré
        newfile = '{0:s}_massif{1:d}.nc'.format(rawfile.rstrip('.nc'), massif_to_extract)
        outputs = Dataset(newfile, 'w', format='NETCDF4')
        outputs.createDimension('time', time.shape[0])
        outputs.createDimension('points', np.size(f.read_var('ZS')[mask]))

        # for time

        # Choose variables and fill the NETCDF file
        #my_list = [x.encode('ascii') for x in f.listvar()]
        outputs.createVariable('time', np.float64, ('time'), fill_value=-9999)
        outputs['time'].use_nc_get_vars(time)

        if filetype == 'pro': 
            VAR_1D = ['ZS', 'aspect', 'slope', 'massif_num', 'longitude', 'latitude']
            VAR_2D = ['TG1', 'TG4', 'MMP_VEG', 'DRAIN_ISBA', 'RUNOFF_ISBA',
                   'SNOMLT_ISBA', 'WSN_T_ISBA', 'DSN_T_ISBA', 'WBT']
        elif filetype == 'forcing':
            VAR_1D = ['ZS', 'aspect', 'slope', 'massif_number']
            VAR_2D = ['Rainf', 'Snowf', 'Tair', 'Qair', 'PSurf', 'Wind_DIR',
                    'Wind', 'LWdown', 'DIR_SWdown', 'SCA_SWdown', 'NEB', 'HUMREL']

        for var1 in VAR_1D:
                outputs.createVariable(var1, np.float64, ('points'), fill_value=-9999)
                outputs[var1][:] = f.read_var(var1)[mask]

        for var2 in VAR_2D:
                outputs.createVariable(
                    var2, np.float64, ('time', 'points'), fill_value=-9999)
                outputs[var2][:] = f.read_var(var2)[:, mask]

        print("Le fichier {0:s} a bien été créé".format(newfile))

        # Close new NETCDF file and remove the old file
        outputs.close()

