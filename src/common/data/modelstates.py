#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import term
from iga.syntax.stdattrs import archivesuffix


class Analysis(GeoFlowResource):

    """
    Class for analysis resource. It can be an atmospheric or surface or full
    analysis (full = atmospheric + surface).
    The analysis can be filtered (filling attribute).
    """
    _footprint = dict(
       info = 'Analysis',
       attr = dict(
           kind = dict(
               values = [ 'analysis', 'analyse', 'atm_analysis' ]
           ),
           nativefmt = dict(
                values = [ 'fa', 'grib', 'lfi' ],
                default = 'fa',
           ),
           filtering = dict(
               values = [ 'dfi' ],
               optional = True,
           ),
           filling = dict(
               values = [ 'surface', 'surf', 'atmospheric', 'atm', 'full' ],
               remap = dict(
                   surface = 'surf',
                   atmospheric = 'atm'
               ),
               default = 'full',
               optional = True,
           )
        )
    )

    @property
    def realkind(self):
        return 'analysis'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if 'surf' in self.filling:
            if re.match('aladin|arome', self.model):
                return 'analyse_surf'
            else:
                return 'analyse_surface1'

        if self.filtering != None:
            if 'aladin' in self.model:
                return 'ANALYSE_DFI'
            else:
                return 'analyse'
        else:
            return 'analyse'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if 'surf' in self.filling:
            return 'surfanalyse'
        else:
            return 'analyse'

    def basename_info(self):
        """Generic information, radical = ``analysis``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = 'analysis',
            src     = [self.filling, self.model],
        )

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        if self.model == 'arome':
            if self.filling == 'surf':
                directory = 'fic_day'
            else:
                directory = 'workdir/analyse'
        elif self.model == 'arpege':
            if self.filling == 'surf':
                directory = 'workdir/analyse'
            else:
                directory = 'autres'
        else:
            if self.filling == 'surf':
                directory = 'autres'
            else:
                directory = 'workdir/analyse'
        return dict(
            fmt       = directory,
            model     = self.model,
            nativefmt = self.nativefmt,
        )


class Historic(GeoFlowResource):
    """
    Class for historical state of a model (e.g. from a forecast).
    """
    _footprint = [
        term,
        dict(
            info = 'Historic forecast file',
            attr = dict(
                kind = dict(
                    values = [ 'historic', 'modelstate' ],
                    remap = dict(
                        modelstate = 'historic'
                    )
                ),
                nativefmt = dict(
                    values = [ 'fa', 'grib', 'lfi' ],
                    default = 'fa',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'historic'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'icmsh'
        midfix = '(histfix:igakey)'
        suffix = ''
        if self.geometry.lam and re.match('testms1|testmp1|testmp2', self.geometry.area):
            suffix = '.r' + archivesuffix(self.model, self.cutoff, self.date)

        name = prefix + midfix + '+' + self.term.fmthour

        if re.match('aladin|arome', self.model):
            name = prefix.upper() + midfix + '+' + self.term.fmthour

        return name + suffix

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.model == 'mesonh':
            return self.model.upper() + '.' + self.geometry.area[:4].upper() + '+' + self.term.fmthour + '.' + self.nativefmt
        else:
            return 'ICMSH' + self.model[:4].upper() + '+' + self.term.fmthour

    def basename_info(self):
        """Generic information, radical = ``historic``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = 'historic',
            src     = self.model,
            term    = self.term.fmthm,
        )


