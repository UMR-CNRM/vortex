#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

import six

import footprints

from vortex.layout.nodes import Task
from bronx.stdtypes.date import yesterday, Period, Time


class S2Mtask(Task):

    nightruntime = Time(hours=3, minutes=20)

    def get_period(self):

        if self.conf.rundate.hour == self.nightruntime.hour:
            dateendanalysis = yesterday(self.conf.rundate.replace(hour=6))
        else:
            dateendanalysis = self.conf.rundate.replace(hour=6)

        if self.conf.previ:
            datebegin = dateendanalysis
            dateend = dateendanalysis + Period(days=4)
        else:
            dateend = dateendanalysis
            if self.conf.rundate.hour == self.conf.nightruntime:
                # The night run performs a 4 day analysis
                datebegin = dateend - Period(days=4)
            else:
                # The daytime runs perform a 1 day analysis
                datebegin = dateend - Period(days=1)

        return datebegin, dateend

    def get_rundate_prep(self):
        if self.conf.previ:
            rundate_prep = self.conf.rundate
        else:
            if self.conf.rundate.hour == self.nightruntime.hour:
                rundate_prep = self.conf.rundate - Period(days=1)
            else:
                rundate_prep = self.conf.rundate.replace(hour=self.conf.nightruntime)
        return rundate_prep

    def get_list_members(self):
        if not self.conf.nmembers:
            raise ValueError
        startmember = int(self.conf.startmember) if hasattr(self.conf, "startmember") else 0
        lastmember = int(self.conf.nmembers) + startmember - 1

        return list(range(startmember, lastmember + 1)), list(range(startmember, lastmember + 2))

    def get_list_geometry(self):
        suffix = '_allslopes'
        if self.conf.geometry == 'postes':
            return self.conf.geometry.area
        elif suffix in self.conf.geometry:
            return list(self.conf.geometry.replace(suffix, ''))

