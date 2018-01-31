#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints

from vortex.data.flow     import FlowResource
from vortex.data.flow     import GeoFlowResource
from common.data.consts import GenvModelResource
from common.data.climfiles import GenericClim

#: Automatic export of  class
__all__ = [ ]


logger = footprints.loggers.getLogger(__name__)

from vortex.syntax.stdattrs import term, month

class EmisSumo(GenvModelResource):
    """
    Emissions files
    """
    _footprint = dict(
        info='Emissions files for sumo',
        attr=dict(
            kind=dict(
                values=['emissumo'],
            ),
            gvar=dict(
                default='mocage_emis_sumo02'
            ),
        )
    )

    @property
    def realkind(self):
        return 'emissumo'

class ChemLimitClim(GenvModelResource):
    """
     Boundary chemical limit conditions climatologic file
    """
    _footprint = dict(
        info='Climatological boundary chemical limit conditions',
        attr=dict(
            kind=dict(
                values=['chemlimit_clim'],
            ),
            gvar=dict(
                default='macc_bc22_moins1_nc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'chemlimit_clim'

class Regrid(GenvModelResource):
    """
    File constant for macc/mocage forecast
    """
    _footprint = dict(
        info='File constant for mocage forecast',
        attr=dict(
            kind=dict(
                values=['regrid'],
            ),
            gvar=dict(
                default='regrid_macc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'regrid'

class Template(GenvModelResource):
    """
    File constant for macc/mocage forecast
    """
    _footprint = dict(
        info='Template file for mocage forecast',
        attr=dict(
            kind=dict(
                values=['template'],
            ),
            gvar=dict(
                default='template_mfm'
            ),
        )
    )

    @property
    def realkind(self):
        return 'template'

class ChemSurf(GenvModelResource):
    """
     Chemical surface scheme
    """
    _footprint = dict(
        info='Chemical surface scheme',
        attr=dict(
            kind=dict(
                values=['chemsurf'],
            ),
            gvar=dict(
                default='chemscheme_surf'
            ),
        )
    )

    @property
    def realkind(self):
        return 'chemsurf'

class MonthClimMisc(GenericClim):
    """
     Monthly miscellaneous climatological files
    """
    _footprint = [
        month,
        dict(
            info='Monthly climatological files',
            attr=dict(
                kind=dict(
                    values=['clim_misc'],
                    ),
                gvar=dict(
                    default='clim_[model]_[source]'
                    ),
                source=dict(
                    values=['jdata','19941998'],
                ),
                model=dict(
                    values=['mocage'],
                    default='mocage',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clim_misc'

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
                    values = ['nc'],
                    default = 'nc',
                    optional=True
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

        return prefix + actualdate.ymdh + '.' + self.nativefmt

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


class FireCst(GenvModelResource):
    """
     Fire constant file - EN COURS DE DEV ne pas utiliser
    """
    _footprint = dict(
        info='Fire constant file',
        attr=dict(
            kind=dict(
                values=['firecst'],
            ),
            gvar=dict(
                default='auxi_sumo2_embb_macc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'firecst'