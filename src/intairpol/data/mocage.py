#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints

from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.syntax.stdattrs import term

#: Automatic export of  class
__all__ = [ ]

logger = footprints.loggers.getLogger(__name__)


class ChemLimit(FlowResource):
    """Boundary chemical limit conditions file."""

    _footprint = [
        term,
        dict(
            info = 'Boundary chemical limit conditions',
            attr = dict(
                kind = dict(
                    values = ['chemlimit'],
                ),
                nativefmt = dict(
                    values = ['netcdf'],
                    default = 'netcdf',
                    optional = True
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'chemlimit'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'bc22_'
        actualdate = self.date + self.term
        fmtremap = dict(netcdf='nc')

        return prefix + actualdate.ymdh + '.' + fmtremap.get(self.nativefmt, self.nativefmt)


class Fire(GeoFlowResource):
    """Fire data file."""

    _footprint = [
        term,
        dict(
            info='Fire data file',
            attr=dict(
                kind=dict(
                    values=['fire'],
                ),
                nativefmt=dict(
                    values=['fa'],
                    default='fa',
                ),
            )
        )
    ]

    @property
    def realkind(self):
            return 'fire'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'EMBB'
        actualdate = self.date + self.term
        return prefix + self.geometry.area + '+' + actualdate.ymd

    def basename_info(self):
        """Generic information for names fabric."""

        return dict(
            radical = 'fire',
            fmt     = self.nativefmt,
            geo     = self._geo2basename_info(),
            term    = self.term.fmthm
        )


class FireObs(GeoFlowResource):
    """Fire observations file. EN COURS DE DEV ne pas utiliser"""

    _footprint = [
        term,
        dict(
            info='Fire observations file',
            attr=dict(
                kind=dict(
                    values=['fireobs'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
            return 'fireobs'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'GFASfires_'
        actualdate = self.date + self.term
        return prefix + actualdate.ymd + '.tar.gz'
