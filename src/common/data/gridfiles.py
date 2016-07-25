#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.data.contents import JsonDictContent
from vortex.data.flow import GeoFlowResource, FlowResource
from vortex.syntax.stdattrs import term
from vortex.tools import env


class GridPoint(GeoFlowResource):
    """
    Class for gridpoint model files calculated in a post-treatment task. Possible formats are 'grib' and 'fa'.
    A gridpoint file can be calculated for files from different sources given by the "origin" attribute.
    """

    _abstract = True
    _footprint = [
        term,
        dict(
            info = 'GridPoint Fields',
            attr = dict(
                origin = dict(
                    values = [
                        'analyse', 'ana', 'guess', 'gss', 'arpege', 'arp', 'arome', 'aro',
                        'aladin', 'ald', 'historic', 'hst', 'forecast', 'fcst', 'era40', 'e40',
                        'era15', 'e15', 'interp', 'sumo', 'filter'
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
        """OLIVE specific naming convention (abstract)."""
        pass

    def archive_basename(self):
        """OP ARCHIVE specific naming convention (abstract)."""
        pass

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
        """Standard path information for IGA inline cache."""
        directory = dict(
            fa = 'fic_day',
            grib = 'bdap'
        )
        return dict(
            fmt       = directory[self.nativefmt],
            nativefmt = self.nativefmt,
            model     = self.model,
        )


class GridPointMap(FlowResource):
    """
    Map of the gridpoint files as produced by fullpos
    """

    _footprint = dict(
        info = 'Gridpoint Files Map',
        attr = dict(
            kind = dict(
                values   = ['gridpointmap', 'gribfilemap', 'fullposmap'],
                remap = dict(fullposmap = 'gridpointmap', )
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
        )
    )

    @property
    def realkind(self):
        return 'gridpointmap'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            src     = [self.model],
        )


class GridPointFullPos(GridPoint):

    _footprint = dict(
        info = 'GridPoint fields as produced by Fullpos',
        attr = dict(
            nativefmt = dict(
                values  = ['fa'],
                default = 'fa',
            ),
        )
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""

        t = self.term.hour
        e = env.current()
        if 'VORTEX_ANA_TERMSHIFT' not in e and self.origin == 'ana':
            t = 0

        name = None
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

        if name is None:
            raise ValueError('Could not build a proper olive name: {!s}'.format(self))

        return name

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""

        deltastr = 'PT' + str(self.term.hour) + 'H'
        deltadate = self.date + deltastr

        name = None
        if self.origin == 'hst':
            name = 'HM' + self.geometry.area + '+' + deltadate.ymdh
        elif self.origin == 'interp':
            name = 'SM' + self.geometry.area + '+' + deltadate.ymd

        if name is None:
            raise ValueError('Could not build a proper archive name: {!s}'.format(self))

        return name


class GridPointExport(GridPoint):

    _footprint = dict(
        info = 'GridPoint fields as exported for dissemination',
        attr = dict(
            nativefmt = dict(
                values  = ['grib'],
                default = 'grib',
            ),
        )
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""

        t = self.term.hour
        e = env.current()
        if 'VORTEX_ANA_TERMSHIFT' not in e and self.origin == 'ana':
            t = 0
        return 'GRID' + self.origin.upper() + self.geometry.area + '+' + self.term.nice(t)

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""

        name = None
        if re.match('aladin|arome', self.model):
            name = 'GRID' + self.geometry.area + 'r' + str(self.date.hour) + '_' + self.term.fmthour
        elif re.match('arp', self.model):
            name = '(gribfix:igakey)'

        if name is None:
            raise ValueError('Could not build a proper archive name: {!s}'.format(self))

        return name


class FilteredGridPointExport(GridPointExport):

    _footprint = dict(
        info = 'GridPoint fields as exported and filtered for dissemination',
        attr = dict(
            filtername = dict(),
        )
    )

    def basename_info(self):
        """Generic information, radical = ``grid``."""
        infos = super(FilteredGridPointExport, self).basename_info()
        infos["filtername"] = self.filtername
        return infos
