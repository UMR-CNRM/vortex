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
                    values = [ 'gridpoint', 'gribfile' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'gridpoint'

    def olive_basename(self):
        """OLIVE specific naming convention."""

        t = self.term
        e = env.current()
        if not 'SWAPP_ANA_TERMSHIFT' in e and self.origin == 'ana':
            t = 0

        if self.nativefmt == 'fa':
            if self.model == 'mocage':
                if self.origin == 'hst':
                    name = 'HM' + self.geometry.area + '+' + str(self.term)
                elif self.origin == 'sumo':
                    deltastr = "P" + str(self.term) + "H"
                    valid = str(self.date.add_delta(deltastr,"yyyymmdd"))
                    name = 'SM' + self.geometry.area + '_void' + '+' + valid
                elif self.origin == 'interp':
                    deltastr = "P" + str(self.term) + "H"
                    valid = str(self.date.add_delta(deltastr,"yyyymmdd"))
                    name = 'SM' + self.geometry.area + '_interp' + '+' + valid
            else:
                name = 'PFFPOS' + self.origin.upper() + self.geometry.area + '+' + self.term.nice(t)
        else:
            name = 'GRID' + self.origin.upper() + self.geometry.area + '+' + self.term.nice(t)

        return name

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""

        if self.nativefmt == 'grib':
            if re.match('aladin|arome', self.model):
                rr = "%d" % int(self.date.get_fmt_date('hh'))
                name = 'GRID' + self.geometry.area + 'r' + rr + '_' + str(self.term)

            rr = archivesuffix(self.model, self.cutoff, self.date)
            if re.match('arp', self.model):
                name = '(gribfix:igakey)'
            return name

        if self.model == 'mocage' and self.nativefmt == 'fa':
            deltastr = "P" + str(self.term) + "H"
            if self.origin == 'hst':
                valid = str(self.date.add_delta(deltastr,"yyyymmddhh"))
                name = 'HM' + self.geometry.area + '+' + valid
            elif self.origin == 'interp':
                valid = str(self.date.add_delta(deltastr,"yyyymmdd"))
                name = 'SM' + self.geometry.area + '+' + valid
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
            format  = self.nativefmt,
            src     = [self.model, source],
            geo     = self.geometry.area,
            term    = self.term
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
