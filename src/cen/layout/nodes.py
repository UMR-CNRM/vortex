#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

import six

import footprints

from bronx.stdtypes.date import yesterday, Period, Time


class S2MTaskMixIn(object):

    nightruntime = Time(hour=3, minute=0)
    firstassimruntime = Time(hour=6, minute=0)
    secondassimruntime = Time(hour=9, minute=0)

    def get_period(self):

        if self.conf.rundate.hour == self.nightruntime.hour:
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
        if self.conf.previ:
            # Standard case: use the analysis of the same runtime
            rundate_prep = self.conf.rundate
            if self.conf.rundate.hour > self.firstassimruntime:
                # First alternate for 09h run: 06h run
                alternates.append((self.conf.rundate.replace(hour=self.firstassimruntime), "assimilation"))
            if self.conf.rundate.hour > self.nightruntime:
                # First alternate for 06h run, second alternate for 09h run: 03h run
                alternates.append((self.conf.rundate.replace(hour=self.nightruntime), "assimilation"))
            # Very last alternates (and only one for 03h run: forecast J+4 of day J-4
            alternates.append((self.conf.rundate.replace(hour=self.secondassimruntime) - Period(days=4), "production"))
            alternates.append((self.conf.rundate.replace(hour=self.firstassimruntime) - Period(days=4), "production"))
            alternates.append((self.conf.rundate.replace(hour=self.nightruntime) - Period(days=4), "production"))

        else:
            # Standard case: use today 03h for 06 et 09h runs, use yesterday 03h for 03h run
            if self.conf.rundate.hour == self.nightruntime.hour:
                rundate_prep = self.conf.rundate - Period(days=1)
            else:
                rundate_prep = self.conf.rundate.replace(hour=self.nightruntime.hour)

            # First alternate : J-2 for night run, J-1 for other runs
            # Second alternate : J-3 for night run, J-2 for other runs
            # Third alternate : J-4 for night run, J-3 for other runs
            alternates.append((rundate_prep - Period(days=1), "assimilation"))
            alternates.append((rundate_prep - Period(days=2), "assimilation"))
            alternates.append((rundate_prep - Period(days=3), "assimilation"))

        return rundate_prep, alternates

    def get_list_members(self):
        if not self.conf.nmembers:
            raise ValueError
        startmember = int(self.conf.startmember) if hasattr(self.conf, "startmember") else 0
        lastmember = int(self.conf.nmembers) + startmember - 1

        return list(range(startmember, lastmember + 1)), list(range(startmember, lastmember + 3))

    def get_list_geometry(self):
        source_safran, block_safran = self.get_source_safran()
        suffix = '_allslopes'
        if source_safran == "safran":
            if self.conf.geometry.area == "postes":
                return self.conf.geometry.list.split(",")
            elif suffix in self.conf.geometry.area:
                return [self.conf.geometry.area.replace(suffix, '')]
        else:
            return [self.conf.geometry.area]

    def get_source_safran(self):
        if self.conf.rundate.hour != self.nightruntime.hour and self.conf.previ:
            return "s2m", "meteo"
        else:
            if self.conf.geometry.area == 'postes':
                return "safran", "postes"
            else:
                return "safran", "massifs"
