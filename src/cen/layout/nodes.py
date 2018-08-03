#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.stdtypes.date import yesterday, Period, Time


class S2MTaskMixIn(object):

    nightruntime = Time(hour=3, minute=0)

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
        if self.conf.previ:
            rundate_prep = self.conf.rundate
        else:
            if self.conf.rundate.hour == self.nightruntime.hour:
                rundate_prep = self.conf.rundate - Period(days=1)
            else:
                rundate_prep = self.conf.rundate.replace(hour=self.nightruntime.hour)
        return rundate_prep

    def get_list_members(self):
        if not self.conf.nmembers:
            raise ValueError
        startmember = int(self.conf.startmember) if hasattr(self.conf, "startmember") else 0
        lastmember = int(self.conf.nmembers) + startmember - 1

        return list(range(startmember, lastmember + 1)), list(range(startmember, lastmember + 2))

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
