#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


import re

from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import term
from iga.syntax.stdattrs import archivesuffix


class Elscf(GeoFlowResource):
    """
    Class of a coupling file for a Limited Area Model. A SpectralGeometry object is needed and the source model is given in the footprint.
    """
    _footprint = [
        term,
        dict(
            info = 'Coupling file for a limited area model',
            attr = dict(
                kind = dict(
                    values = [ 'elscf' ]
                ),
                nativefmt = dict(
                    values = [ 'fa', 'grib' ],
                    default = 'fa',
                ),
                source = dict(
                    values = [ 'arpege', 'aladin', 'arome', 'ifs', 'ecmwf' ]
                ),
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'elscf'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'ELSCF' + self.model[:4].upper() + '_' + self.geometry.area + '+' + str(self.term)

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        suffix = archivesuffix(self.model, self.cutoff, self.date)
        prefix = 'COUPL'
        if re.match('assist1bis|testms1', self.geometry.area):
            prefix = 'COUPL1'
        if re.match('ifs|ecmwf', self.source) and '16km' in self.geometry.resolution:
            prefix = 'COUPLIFS'

        return prefix + str(self.term) + '.r' + str(suffix)

    def basename_info(self):
        """Generic information, radical = ``cpl``."""
        return dict(
            format  = self.nativefmt,
            geo     = [self.geometry.area, self.geometry.resolution],
            src     = self.source,
            radical = 'cpl',
            term    = str(self.term),
        )

    def iga_pathinfo(self):
        if self.model == 'arome':
            directory = 'fic_day'
        else:
            directory = 'autres'
        return dict(
            fmt       =  directory,
            model     = self.model,
            nativefmt = self.nativefmt,
        )
