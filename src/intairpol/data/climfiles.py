#!/usr/bin/env python
# -*- coding: utf-8 -*-

from vortex.syntax.stdattrs import month
from common.data.consts import GenvModelResource
from common.data.climfiles import GenericClim

#: No automatic export
__all__ = []


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
            nativefmt=dict(
                optional=True,
                default='netcdf',
            )
        )
    )

    @property
    def realkind(self):
        return 'chemlimit_clim'


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
                    values=['jdata', '19941998'],
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