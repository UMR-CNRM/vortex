#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

import footprints

from vortex.data.contents     import TextContent
from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.syntax.stdattrs import term, a_domain


#: Automatic export of  class
__all__ = [ ]

logger = footprints.loggers.getLogger(__name__)


class ChemicalBoundaryConditions(FlowResource):
    """Chemical boundary conditions produced by some external model."""

    _footprint = [
        term,
        dict(
            info = 'Chemical boundary conditions',
            attr = dict(
                kind = dict(
                    values   = ['chemical_bc'],
                ),
                nativefmt = dict(
                    values   = ['netcdf'],
                    default  = 'netcdf',
                    optional = True
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'chemical_bc'

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
            info = 'Fire data file',
            attr = dict(
                kind = dict(
                    values  = ['fire'],
                ),
                nativefmt = dict(
                    values  = ['fa'],
                    default = 'fa',
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


class ObsFire(GeoFlowResource):
    """Fire observations file."""

    _footprint = [
        term,
        dict(
            info = 'Fire observations file',
            attr = dict(
                kind = dict(
                    values = ['obsfire'],
                ),
                nativefmt = dict(
                    values   = ['obsfirepack'],
                    default  = 'obsfirepack',
                    optional = True
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'obsfire'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'GFASfires_'
        actualdate = self.date + self.term
        return prefix + actualdate.ymd + '.tar.gz'

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = 'obsfire',
            geo     = self._geo2basename_info(),
            term    = self.term.fmthm
        )

class TopBoundaryCondition(FlowResource):
    """Boundary conditions on top of the model, e.g. mocage."""

    _footprint = dict(
        info = 'Top Boundary Conditions',
        attr = dict(
            kind = dict(
                values   = ['topbd'],
            ),
            model = dict(
                values   = ['mocage'],
                default  = 'mocage',
                optional = True,
            ),
        )
    )

    @property
    def realkind(self):
        return 'topbd'

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            src     = self.model,
        )


class PostPeriodicStats(GeoFlowResource):
    """Stats computed on a defined forecast period."""

    _footprint = [
        term,
        dict(
            info = 'Stats computed on a defined forecast period',
            attr = dict(
                kind = dict(
                    values  = ['ppstats'],
                ),
                nativefmt = dict(
                    values  = ['netcdf'],
                    default = 'netcdf',
                ),
                run_eval = dict(
                    values = ['first_level', 'stats', 'base'],
                    remap = dict(base = 'stats'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ppstats'

    def basename_info(self):
        """Generic information for names fabric for these stats."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            term    = self.term.fmthm,
            geo     = self._geo2basename_info(),
            src     = [self.model, self.run_eval],
        )


class RestartFlagContent(TextContent):
    """Specialisation of the TextContent"""
    @property
    def restart(self):
        """Retrieves content file"""
        return(int(self.data[0][0]))

    def if_restart(self, restartvalue, nominalvalue):
        return(restartvalue if self.restart else nominalvalue)


class RestartFlag(FlowResource):
    """Restart flag between tasks test_restart and clim_restart"""

    _footprint = [
        dict(
            info = 'Restart flag',
            attr = dict(
                kind = dict(
                    values  = ['restart_flag'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
                clscontents=dict(
                    default=RestartFlagContent,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'restart_flag'

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = 'clim_restart',
            fmt     = self.nativefmt,
        )
