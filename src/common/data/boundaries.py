#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


import re

from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import term
from iga.syntax.stdattrs import archivesuffix


class LAMBoundary(GeoFlowResource):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed and the source model is given in the footprint.
    """
    _footprint = [
        term,
        dict(
            info = 'Coupling file for a limited area model',
            attr = dict(
                kind = dict(
                    values  = ['boundary', 'elscf', 'coupled'],
                    remap   = dict(
                        elscf = 'boundary',
                        coupled = 'boundary'
                    )
                ),
                nativefmt = dict(
                    values  = ['fa', 'grib'],
                    default = 'fa',
                ),
                source = dict(
                    values  = ['arpege', 'aladin', 'arome', 'ifs', 'ecmwf']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'boundary'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'ELSCF' + self.model[:4].upper() + '_' + self.geometry.area + '+' + self.term.fmthour

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        suffix = archivesuffix(self.model, self.cutoff, self.date)
        prefix = 'COUPL'
        if re.match('assist1bis|testms1', self.geometry.area):
            prefix = 'COUPL1'
        if re.match('ifs|ecmwf', self.source) and '16km' in self.geometry.rnice:
            prefix = 'COUPLIFS'

        return prefix + self.term.fmthour + '.r' + str(suffix)

    def basename_info(self):
        """Generic information, radical = ``cpl``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [self.geometry.area, self.geometry.rnice],
            src     = self.source,
            radical = 'cpl',
            term    = self.term.fmthm,
        )

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        if self.model == 'arome':
            directory = 'fic_day'
        else:
            directory = 'autres'
        return dict(
            fmt       = directory,
            model     = self.model,
            nativefmt = self.nativefmt,
        )
