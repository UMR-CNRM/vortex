#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.data.flow import GeoFlowResource
from vortex.data.geometries import GridGeometry
from vortex.syntax.stdattrs import term
from iga.syntax.stdattrs import archivesuffix
from vortex.tools import env


class Gridpoint(GeoFlowResource):

    """
    Class for gridpoint model files calculated in a post-treatment task. Possible formats are 'grib' and 'fa'.
    A gridpoint file can be calculated for files from different sources given by the "origin" attribute.
    """

    _footprint = [
        term,
        dict(
            info = 'Grib file',
            attr = dict(
                origin = dict(
                    values = [
                        'analyse','ana', 'guess', 'gss', 'arpege','arp', 'arome', 'aro','aladin', 'ald',
                        'historic','hst', 'forecast','fcst','era40','e40', 'era15','e15', 'interp', 'sumo'
                    ],
                    remap = dict(
                        analyse = 'ana',
                        guess = 'gss',
                        arpege = 'arp',
                        aladin = 'ald',
                        arome = 'aro',
                        historic = 'hst',
                        forecast = 'fcst',
                        era40 = 'e40',
                        era15 = 'e15'
                    )
                ),
                nativefmt = dict(
                    values = [ 'fa', 'grib'],
                ),
                geometry = dict(
                    type = GridGeometry,
                ),
                kind = dict(
                    values = [ 'gridpoint', 'gribfile', 'fullpos' ],
                    remap = dict(
                        fullpos = 'gridpoint'
                    )
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'gridpoint'

    def olive_basename(self):
        """OLIVE specific naming convention."""

        t = self.term.hour
        e = env.current()
        if not 'SWAPP_ANA_TERMSHIFT' in e and self.origin == 'ana':
            t = 0

        if self.nativefmt == 'fa':
            if self.model == 'mocage':
                if self.origin == 'hst':
                    name = 'HM' + self.geometry.area + '+' + self.term.fmthour
                elif self.origin == 'sumo':
                    deltastr = 'PT' + str(self.term.hour) + 'H'
                    deltadate = self.date + deltastr
                    name = 'SM' + self.geometry.area + '_void' + '+' + deltadate.ymd
                elif self.origin == 'interp':
                    deltastr = 'PT' + str(self.term.hour) + 'H'
                    deltadate = self.date + deltastr
                    name = 'SM' + self.geometry.area + '_interp' + '+' + deltadate.ymd
            else:
                name = 'PFFPOS' + self.origin.upper() + self.geometry.area + '+' + self.term.nice(t)
        else:
            name = 'GRID' + self.origin.upper() + self.geometry.area + '+' + self.term.nice(t)

        return name

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""

        if self.nativefmt == 'grib':
            if re.match('aladin|arome', self.model):
                name = 'GRID' + self.geometry.area + 'r' + str(self.date.hour) + '_' + self.term.fmthour

            rr = archivesuffix(self.model, self.cutoff, self.date)
            if re.match('arp', self.model):
                name = '(gribfix:igakey)'
            return name

        if self.model == 'mocage' and self.nativefmt == 'fa':
            deltastr = 'PT' + str(self.term.hour) + 'H'
            deltadate = self.date + deltastr
            if self.origin == 'hst':
                name = 'HM' + self.geometry.area + '+' + deltadate.ymdh
            elif self.origin == 'interp':
                name = 'SM' + self.geometry.area + '+' + deltadate.ymd
            return name

    def basename_info(self):
        """Generic information, radical = ``grid``."""

        if self.model == 'mocage':
            if self.origin == 'hst':
                source = 'forecast'
            else:
                source = 'sumo'
        else:
            source = 'forecast'

        return dict(
            radical = 'grid',
            fmt     = self.nativefmt,
            src     = [self.model, source],
            geo     = self.geometry.area,
            term    = self.term.fmthm
        )

    def iga_pathinfo(self):
        directory = dict(
            fa = 'fic_day',
            grib = 'bdap'
        )
        return dict(
            fmt       = directory[self.nativefmt],
            nativefmt = self.nativefmt,
            model     = self.model,
        )
