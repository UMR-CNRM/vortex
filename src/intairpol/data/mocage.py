#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

from bronx.fancies import loggers

from vortex.data.contents import TextContent
from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.syntax.stdattrs import term_deco
from vortex.syntax.stddeco import namebuilding_append, namebuilding_delete, namebuilding_insert

#: Automatic export of  class
__all__ = [ ]

logger = loggers.getLogger(__name__)


@namebuilding_delete('src')
class ChemicalBoundaryConditions(GeoFlowResource):
    """Chemical boundary conditions produced by some external model."""

    _footprint = [
        term_deco,
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
                oparchive_prefix = dict(
                    default = 'bc22_',
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
        actualdate = self.date + self.term
        fmtremap = dict(netcdf='nc')
        return self.oparchive_prefix + actualdate.ymdh + '.' + fmtremap.get(self.nativefmt, self.nativefmt)


@namebuilding_delete('src')
class Fire(GeoFlowResource):
    """Fire data file."""

    _footprint = [
        term_deco,
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


@namebuilding_delete('src')
@namebuilding_delete('fmt')
class ObsFire(GeoFlowResource):
    """Fire observations file."""

    _footprint = [
        term_deco,
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


@namebuilding_delete('fmt')
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


@namebuilding_append('src', lambda s: s.run_eval)
class PostPeriodicStats(GeoFlowResource):
    """Stats computed on a defined forecast period."""

    _footprint = [
        term_deco,
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


class RestartFlagContent(TextContent):
    """Specialisation of the TextContent"""

    @property
    def restart(self):
        """Retrieves content file"""
        return int(self.data[0][0])

    def if_restart(self, restartvalue, nominalvalue):
        return restartvalue if self.restart else nominalvalue


@namebuilding_insert('radical', lambda s: 'clim_restart')
@namebuilding_delete('src')
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
